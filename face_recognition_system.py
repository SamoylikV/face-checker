import cv2
import face_recognition
import numpy as np
import threading
import queue
import time
from database import Database
from settings import DB_PARAMS, MODEL_WEIGHTS, MODEL_CONFIG, VIDEO_SOURCE


class FaceRecognitionSystem:
    def __init__(self, video_source=VIDEO_SOURCE, model_weights=MODEL_WEIGHTS, model_config=MODEL_CONFIG,
                 db_params=DB_PARAMS):
        self.db = Database(db_params)

        self.net = cv2.dnn.readNet(model_weights, model_config)
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]

        self.face_dict = self.db.load_face_encodings()
        self.cap = cv2.VideoCapture(video_source)

        self.frame_skip = 1
        self.display_queue = queue.Queue()
        self.exit_flag = threading.Event()

    def detect_faces(self, frame):
        height, width, channels = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

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

    def process_frame(self, frame):
        faces = self.detect_faces(frame)

        current_frame_positions = {}

        for (x, y, w, h) in faces:
            face_image = frame[y:y + h, x:x + w]

            if face_image.shape[0] > 0 and face_image.shape[1] > 0:
                face_image_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                face_encoding = face_recognition.face_encodings(face_image_rgb)

                if face_encoding:
                    matches = face_recognition.compare_faces([encoding for encoding, _ in self.face_dict.values()],
                                                             face_encoding[0], tolerance=0.7)
                    match_indices = [i for i, match in enumerate(matches) if match]

                    if match_indices:
                        first_match_index = match_indices[0]
                        face_id = list(self.face_dict.keys())[first_match_index]
                        _, name = self.face_dict[face_id]

                        if face_id in current_frame_positions:
                            continue

                        current_frame_positions[face_id] = (x, y, x + w, y + h)
                        self.db.update_face_encoding(face_id, face_encoding[0], f"faces/face_{face_id}.jpg")
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, name if name else f"Person {face_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.9, (0, 255, 0), 2)

                    else:
                        face_id = len(self.face_dict) + 1
                        self.face_dict[face_id] = (face_encoding[0] if face_encoding else None, None)

                        cv2.imwrite(f"faces/face_{face_id}.jpg", face_image)
                        self.db.insert_face_dict(face_id, (face_encoding[0], None), f"faces/face_{face_id}.jpg")

                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                        cv2.putText(frame, f"Person {face_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255),
                                    2)

        self.display_queue.put(frame)

    def video_capture_thread(self):
        frame_count = 0
        while not self.exit_flag.is_set():
            ret, frame = self.cap.read()
            frame_count += 1
            if self.display_queue.qsize() > 10:
                time.sleep(0.01)
                continue
            if frame_count % self.frame_skip != 0:
                continue
            self.process_frame(frame)
            for face_id, encoding in self.face_dict.items():
                self.db.insert_face_dict(face_id, encoding, f"faces/face_{face_id}.jpg")
        self.cap.release()

    def start_system(self):
        video_thread = threading.Thread(target=self.video_capture_thread, daemon=True)
        video_thread.start()

        try:
            while not self.exit_flag.is_set():
                try:
                    frame = self.display_queue.get_nowait()
                    cv2.imshow("Face Recognition", frame)

                    key = cv2.waitKey(1)
                    if key & 0xFF == ord('q'):
                        self.exit_flag.set()
                        break
                except Exception as e:
                    pass
                time.sleep(0.01)

        finally:
            video_thread.join()
            self.release_resources()

    def release_resources(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.db.close()
