import cv2
import face_recognition
import numpy as np
import threading
import queue
import time

def detect_faces(frame, net, output_layers):
    height, width, channels = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    faces = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5 and class_id == 0:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                faces.append((x, y, w, h))

    return faces

def process_frame(frame, net, output_layers, face_dict, display_queue):
    faces = detect_faces(frame, net, output_layers)

    current_frame_positions = {}

    for (x, y, w, h) in faces:
        face_image = frame[y:y + h, x:x + w]

        if face_image.shape[0] > 0 and face_image.shape[1] > 0:
            face_image_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            face_encoding = face_recognition.face_encodings(face_image_rgb)

            if face_encoding:
                matches = face_recognition.compare_faces(list(face_dict.values()), face_encoding[0], tolerance=0.7)
                match_indices = [i for i, match in enumerate(matches) if match]

                if match_indices:
                    first_match_index = match_indices[0]
                    face_id = list(face_dict.keys())[first_match_index]

                    if face_id in current_frame_positions:
                        continue

                    current_frame_positions[face_id] = (x, y, x + w, y + h)

                else:
                    face_id = len(face_dict) + 1
                    face_dict[face_id] = face_encoding[0] if face_encoding else None

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"Person {face_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    display_queue.put(frame)

def video_capture_thread(cap, net, output_layers, face_dict, frame_skip, display_queue, exit_flag):
    frame_count = 0
    while not exit_flag.is_set():
        ret, frame = cap.read()
        frame_count += 1
        if display_queue.qsize() > 10:
            time.sleep(0.01)
            continue

        if frame_count % frame_skip != 0:
            continue

        process_frame(frame, net, output_layers, face_dict, display_queue)

    cap.release()

# net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
net = cv2.dnn.readNet("yolov4-tiny.weights", "yolov4-tiny.cfg")

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

face_dict = {}

cap = cv2.VideoCapture(0)

frame_skip = 1
display_queue = queue.Queue()

exit_flag = threading.Event()

video_thread1 = threading.Thread(target=video_capture_thread, args=(cap, net, output_layers, face_dict, frame_skip, display_queue, exit_flag), daemon=True)
video_thread1.start()

try:
    while not exit_flag.is_set():
        try:
            frame = display_queue.get_nowait()

            cv2.imshow("Face Recognition", frame)

            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                exit_flag.set()
                break

        except queue.Empty:
            pass
        time.sleep(0.01)


finally:
    video_thread1.join()
    cv2.destroyAllWindows()