/* Mock Door Tweet
   gang programmed by VHS (c) copyright 2009.
   goldfish vanjuggler tristan danv
   see LICENSE file for full details.
*/

#define doorPin (4)
#define bathroomDoorPin (7)
#define tempPin (0)
#define INPUT_BUFFER(S) (strcmp((S), buffer) == 0)

//  Incoming serial msg buffer
#define BUFSIZE 256
char buffer[BUFSIZE];
int buffer_idx = 0;

void setup() {
    Serial.begin( 9600 );
}

///  Check serial port for incoming messages and update global buffer
int checkSerialCommand() {
    int pending = 0;

    if (buffer_idx == 0) {
        memset(buffer, 0, BUFSIZE);
    }

    // Read an incoming command
    // if bytes are available, addthemto the buffer
    int incoming = Serial.available();
    while (incoming-- > 0) {
        char foo = Serial.read();

        if (foo == '\n') {
            pending = 1;
            buffer[buffer_idx++] = 0;
            buffer_idx = 0;
            Serial.print("#RECV: ");
            Serial.println(buffer);
        }
        else {
            buffer[buffer_idx++] = foo;
            buffer[buffer_idx] = 0;
        }
    }

    return pending;
}

int cycles = 0;
bool doorOpen = false;

void loop() {
    if (checkSerialCommand()) {
        if (INPUT_BUFFER("temperature")) {
            Serial.println("temperature 24.44C");
        }
        else if (INPUT_BUFFER("buzz")) {
          Serial.println("buzz played");
        }
        else {
          Serial.print(buffer);
          Serial.println(" !unknown command");
        }
    }

    if (++cycles % 100 == 0) {
      if (doorOpen) {
        Serial.println("door open");
      }
      else {
        Serial.println("door closed");
      }
      doorOpen = !doorOpen;
    }
    
    delay(100);
}
