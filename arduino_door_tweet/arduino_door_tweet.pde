/* Door Tweet
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

int doorPinState;
int bathroomDoorPinState;

void setup() {
    Serial.begin( 9600 );

    // set input pins & pull-ups
    pinMode( doorPin, INPUT );
    pinMode( tempPin, INPUT );
    pinMode( bathroomDoorPin, INPUT );
    digitalWrite( doorPin, HIGH ); 
    digitalWrite( tempPin, HIGH );
    digitalWrite( bathroomDoorPin, HIGH );

    doorPinState = digitalRead( doorPin );
    bathroomDoorPinState = digitalRead( bathroomDoorPin );
}

/// Read temperature from supplied pin
float readTemperature(int pin)
{
    int temp = analogRead(tempPin);
    float voltage = temp * 5.0f / 1024;
    float celsius = (voltage - 0.5f) * 100;
    return celsius;
}

///  Check door status and update global doorPinState
int checkDoor() {
    int newDoorPinState;

    newDoorPinState = digitalRead( doorPin );
    if( doorPinState != newDoorPinState ){
        doorPinState = newDoorPinState;
        return 1;
    }
    return 0;
}

///  Check door status and update global doorPinState
int checkBathroomDoor() {
    int newBathroomDoorPinState;

    newBathroomDoorPinState = digitalRead( bathroomDoorPin );
    if( bathroomDoorPinState != newBathroomDoorPinState ){
        bathroomDoorPinState = newBathroomDoorPinState;
        return 1;
    }
    return 0;
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
            Serial.println( buffer );
        }
        else {
            buffer[buffer_idx++] = foo;
            buffer[buffer_idx] = 0;
        }
    }

    return pending;
}

void loop() {
    if (checkDoor()) {
        if( doorPinState == 0 ){
            // door open
            Serial.println( "door open" );
            digitalWrite( 13, HIGH );
        }
        else{
            // door closed
            Serial.println( "door closed" );
            digitalWrite( 13, LOW );
        }
    }
    
    if( checkBathroomDoor() ){
        if( bathroomDoorPinState == 0 ){
            // bathroom door open
            Serial.println( "bathroom door closed" );
        }
        else{
            // bathroom door closed
            Serial.println( "bathroom door open" );
        }
    }

    if (checkSerialCommand()) {
        if (INPUT_BUFFER("temperature")) {
            float temp = readTemperature(tempPin);
            Serial.print("temperature ");
            Serial.print(temp);
            Serial.println('C');
        }
    }
}

