/* Door Tweet
   gang programmed by VHS (c) copyright 2009.
   goldfish vanjuggler tristan danv
   see LICENSE file for full details.
*/

#define doorPin (4)
#define bathroomDoorPin (7)
#define tempPin (0)
#define buzzerPin (8)
#define INPUT_BUFFER(S) (strcmp((S), buffer) == 0)

//  Incoming serial msg buffer
#define BUFSIZE 256
char buffer[BUFSIZE];
int buffer_idx = 0;

//  Musical note table, frequencies in Hz
int NOTES[] = {
    2093,  // C7
    2349,  // D7
    2637,  // E7
    2794,  // F7
    3136,  // G7
    3520,  // A7
    3951,  // B7
    4186,  // C8
};

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

    //  reset piezo
    digitalWrite( buzzerPin, LOW);

    doorPinState = digitalRead( doorPin );
    bathroomDoorPinState = digitalRead( bathroomDoorPin );

    // transform note frequencies to periods
    for (int i=0; i < 8; ++i) {
        NOTES[i] = 1e6 / NOTES[i];
    }
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

/**
 * Print a door's state to serial line
 *
 * @param doorState pointer to door state to check
 * @param doorName name of door to use in serial output
 */
void print_door_state(int* doorState, const char* doorName)
{
    if( *doorState == 0 ) {
        // door open
        Serial.print(doorName);
        Serial.println( " open" );
        // digitalWrite( 13, HIGH ); ???
    }
    else {
        // door closed
        Serial.print(doorName);
        Serial.println( " closed" );
        // digitalWrite( 13, LOW );  ???
    }
}

/**
 * Sound a given note on the buzzer for a specified duration
 *
 * @param note note table index (0-7)
 * @param duration duration of buzz in microseconds
 */
int buzz(int note, long duration)
{
    if (note >= 0 && note < 8) {
        int period = NOTES[note] / 2;
        long elapsed_time = 0;

        while (elapsed_time < duration) {
            // square wave
            digitalWrite(buzzerPin, HIGH);
            delayMicroseconds(period);
            digitalWrite(buzzerPin, LOW);
            delayMicroseconds(period);
            elapsed_time += period;
        }
        return 1;
    }
    // invalid note, return fail
    return 0;
}

void loop() {
    const char* door_name = "door";
    const char* bathroom_door_name = "bathroom";

    //  Poll & push events to serial
    if (checkDoor()) {
        print_door_state(&doorPinState, door_name);
    }
    
    if (checkBathroomDoor()) {
        print_door_state(&bathroomDoorPinState, bathroom_door_name);
    }

    //  Respond to incoming serial commands
    if (checkSerialCommand()) {
        if (INPUT_BUFFER("temperature")) {
            float temp = readTemperature(tempPin);
            Serial.print("temperature ");
            Serial.print(temp);
            Serial.println('C');
        }
        else if (INPUT_BUFFER("door state")) {
            print_door_state(&doorPinState, door_name);
        }
        else if (INPUT_BUFFER("bathroom door state")) {
            print_door_state(&bathroomDoorPinState, bathroom_door_name);
        }
        else if (INPUT_BUFFER("buzz")) {
            buzz(0, 2e6);
        }
    }
}

