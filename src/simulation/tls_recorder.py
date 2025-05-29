class TLSEventRecorder:
    """
    Recorder for TLS events
        - tracks seeing them
        - tracks running them
    """
    def __init__(self):
        self.amber_encounters = 0
        self.red_encounters = 0
        self.green_encounters = 0
        self.amber_runs = 0
        self.red_runs = 0
        self.green_runs = 0

    def saw_amber(self):
        self.amber_encounters += 1

    def saw_red(self):
        self.red_encounters += 1

    def saw_green(self):
        self.green_encounters += 1

    def ran_amber(self):
        self.amber_runs += 1

    def ran_red(self):
        self.red_runs += 1

    def ran_green(self):
        self.green_runs += 1
