class UserState:
    def __init__(self, role='user'):
        self.sent_messages = []
        self.current_face_id_message = None
        self.face_id_to_message_id = {}
        self.current_page_message_id = None
        self.role = role
