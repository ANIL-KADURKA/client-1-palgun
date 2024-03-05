from ultralytics import YOLO
import cv2
import math

# from ultralytics import YOLO
# import cv2
import torch
import numpy as np
from sort.sortn import Sort
from filterpy.kalman import KalmanFilter
from umodia import get_car, read_license_plate, write_csv
from flask import Flask, render_template, Response,session


# cv2.destroyAllWindows()
# def video_detection(path_x):
#     pass
    

def video_detection(path_x):
    # Check for GPU availability and set the device
    device = torch.device("cpu")
    results = {}
    mot_tracker = Sort()

    # Load models and move them to the GPU
    coco_model = YOLO('yolov8n.pt')
    license_plate_detector = YOLO('plate23.pt')

    # Load video
    video_capture = path_x
    #Create a Webcam Object
    cap=cv2.VideoCapture(video_capture)
    # cap = cv2.VideoCapture('hitec.mp4')                                                
    vehicles = [2, 3, 5, 7]

    license_plate_numbers = {}

    # Get the video frame dimensions and set up VideoWriter
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    out = cv2.VideoWriter('output.mp4', cv2.VideoWriter_fourcc(*'XVID'), 20.0, (frame_width, frame_height))

    def update_license_plate_dict(license_plate_dict, car_id, license_plate_text, confidence_score):
        if car_id not in license_plate_dict:
            license_plate_dict[car_id] = {'license_plate': license_plate_text, 'confidence_score': confidence_score}
        else:
            previous_confidence_score = license_plate_dict[car_id]['confidence_score']
            if confidence_score > previous_confidence_score:
                license_plate_dict[car_id]['license_plate'] = license_plate_text
                license_plate_dict[car_id]['confidence_score'] = confidence_score

    # Initialize license_plate_dict
    license_plate_dict = {}

    # Initialize Kalman filters for each tracked object
    kalman_filters = {}
    license_plate_info = {}
    license_full = {}
    license_length = {}
    license_final = {}

    # Read frames
    frame_nmr = -1
    ret = True
    encoded_frames = []
    while ret:
        frame_nmr += 1
        ret, frame = cap.read()
        if ret:
            results[frame_nmr] = {}
           
            detections = coco_model(frame)[0]
            detections_ = []
            for detection in detections.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = detection
                if int(class_id) in vehicles:
                    detections_.append([x1, y1, x2, y2, score])

        
            track_ids = mot_tracker.update(np.asarray(detections_))

       
            license_plates = license_plate_detector(frame)[0]
            for license_plate in license_plates.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = license_plate

           
                xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)

                if car_id != -1:
                    if car_id not in kalman_filters:
                        kalman_filters[car_id] = KalmanFilter(dim_x=4, dim_z=2)
                        kalman_filters[car_id].F = np.array([[1, 0, 1, 0],
                                                            [0, 1, 0, 1],
                                                            [0, 0, 1, 0],
                                                            [0, 0, 0, 1]])
                        kalman_filters[car_id].H = np.array([[1, 0, 0, 0],
                                                            [0, 1, 0, 0]])
                        kalman_filters[car_id].P *= 1e3
                        kalman_filters[car_id].R = np.diag([1, 1])  # Measurement noise
                        kalman_filters[car_id].Q = np.diag([1e-2, 1e-2, 1e-2, 1e-2])  # Process noise

                    kalman_filter = kalman_filters[car_id]

                    # Update Kalman filter with new measurement
                    measurement = np.array([[xcar1], [ycar1]])
                    kalman_filter.predict()
                    kalman_filter.update(measurement)

                    # Get predicted location from Kalman filter
                    xcar1_kf, ycar1_kf, _, _ = kalman_filter.x
                    xcar2_kf, ycar2_kf = xcar1_kf + (xcar2 - xcar1), ycar1_kf + (ycar2 - ycar1)

                    # Crop license plate
                    license_plate_crop = frame[int(y1):int(y2), int(x1): int(x2), :]

                    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                    _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

                    # Read license plate number
                    license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

                    if license_plate_text is not None:
                        # Update license_plate_dict dictionary
                        update_license_plate_dict(license_plate_dict, car_id, license_plate_text, license_plate_text_score)

                        # Display the most confident license plate text
                        text = license_plate_dict[car_id]['license_plate']

                        # Update license_plate_info dictionary
                        if car_id not in license_plate_info:
                            license_plate_info[car_id] = {}

                        # Store license plate information directly
                        license_plate_info[car_id]['licence_plate_number'] = license_plate_text
                        license_plate_info[car_id]['confidence_score'] = license_plate_text_score

                        # Check the length of the detected license plate number
                        if len(license_plate_text) == 10:
                            # Update license_full dictionary
                            if car_id not in license_full:
                                license_full[car_id] = {}

                            # Check and update if the current confidence score is greater than the previous one
                            previous_confidence_score_full = license_full[car_id].get('confidence_score', 0)
                            if license_plate_text_score > previous_confidence_score_full:
                                license_full[car_id]['licence_plate_number'] = license_plate_text
                            license_full[car_id]['confidence_score'] = license_plate_text_score
                        else:
                            # Update license_length dictionary for license plates with lengths other than 10
                            if car_id not in license_length:
                                license_length[car_id] = {}

                            # Check if the current license plate length is greater than or equal to the previous one for the same car ID
                            previous_license_plate_length = len(license_length[car_id].get('licence_plate_number', ''))
                            if len(license_plate_text) > previous_license_plate_length or \
                            (len(license_plate_text) == previous_license_plate_length and license_plate_text_score > license_length[car_id].get('confidence_score', 0)):
                                # Store license plate information directly
                                license_length[car_id]['licence_plate_number'] = license_plate_text
                                license_length[car_id]['confidence_score'] = license_plate_text_score

                        # Update license_final with data from license_length
                        for half_car_id, half_info in license_length.items():
                            license_final[half_car_id] = {
                                'licence_plate_number': half_info.get('licence_plate_number', ''),
                                'confidence_score': half_info.get('confidence_score', 0)
                            }

                        # Check if corresponding car_id is present in license_full, and if so, update license_final
                        for full_car_id, full_info in license_full.items():
                            if full_car_id in license_final:
                                # Prefer license_full information for common keys
                                license_final[full_car_id]['licence_plate_number'] = full_info.get('licence_plate_number', '')
                                license_final[full_car_id]['confidence_score'] = full_info.get('confidence_score', 0)

                        results[frame_nmr][car_id] = {
                            'car': {'bbox': [xcar1_kf, ycar1_kf, xcar2_kf, ycar2_kf]},
                            'license_plate': {
                                'bbox': [x1, y1, x2, y2],
                                'text': license_final.get(car_id, {}).get('licence_plate_number', ''),
                                'bbox_score': score,
                                'text_score': license_final.get(car_id, {}).get('confidence_score', 0)
                            }
                        }

                        license_plate_numbers[car_id] = license_plate_text



            # print("License_full:", license_full)
            # print("license_length:", license_length)
            # print("License_final:", license_final)
            # session['anil']=license_final
            hello = license_final
            # print(".........................................")
            # print(hello)

         
            for car_id, data in results[frame_nmr].items():
                car_bbox = data['car']['bbox']
                license_plate_bbox = data['license_plate']['bbox']
                text = data['license_plate']['text']

                # Draw very thick light blue bounding box around the car
                cv2.rectangle(frame, (int(car_bbox[0]), int(car_bbox[1])), (int(car_bbox[2]), int(car_bbox[3])),
                            (173, 216, 230), 5)

                # Draw very thick red bounding box around the license plate
                cv2.rectangle(frame, (int(license_plate_bbox[0]), int(license_plate_bbox[1])),
                            (int(license_plate_bbox[2]), int(license_plate_bbox[3])), (0, 0, 255), 5)

                # Display license plate text above the bounding box with larger, thicker font
                cv2.putText(frame, text, (int(license_plate_bbox[0]), int(license_plate_bbox[1]) - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
           
            yield frame


            yield license_final
        
       
            # out.write(frame)

            # # Display the current frame
            # cv2.imshow("Frame", frame)
            # retval, buffer = cv2.imencode('.jpg', frame)
            # frame_base64 = base64.b64encode(buffer).decode('utf-8')
            # encoded_frames.append(frame_base64)



           

            # # Check for a key press and break the loop if the user presses 'q'
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

        

    

    # Release the VideoWriter and capture objects
    # out.release()
    # cap.release()
    cv2.destroyAllWindows()

    # Print the dictionary of license plate numbers
    # print("Detected License Plate Numbers:")
    # for car_id, plate_info in license_final.items():
    #     print(f"Car ID {car_id}: License Plate Number: {plate_info['licence_plate_number']}, Confidence: {plate_info['confidence_score']}")



