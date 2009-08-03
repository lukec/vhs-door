/* Door Tweet
   gang programmed by VHS (c) copyright 2009.
   goldfish vanjuggler tristan
   see LICENSE file for full details.
*/

#define doorPin (4)
#define tempPin (0)

//  Incoming serial msg buffer
#define BUFSIZE 256
char buffer[256];

int doorPinState;


void setup() {
    Serial.begin( 9600 );

    // set input pins & pull-ups
    pinMode( doorPin, INPUT );
    pinMode( tempPin, INPUT );
    digitalWrite( doorPin, HIGH ); 
    digitalWrite( tempPin, HIGH );

    doorPinState = digitalRead( doorPin );
}

/// Read temperature from supplied pin
float readTemperature(int pin)
{
    int temp = analogRead(tempPin);
    float voltage = temp * 5.0f / 1024;
    float celsius = (voltage - 0.5f) * 100;
    return temp;
}

///  Check door status and update global doorPinState
void checkDoor() {
    int newDoorPinState;

    newDoorPinState = digitalRead( doorPin );
    if( doorPinState != newDoorPinState ){
        doorPinState = newDoorPinState;
    }
}

///  Check serial port for incoming messages and update global buffer
int checkSerialCommand() {
    int pending = 0;

    // Read an incoming command
    if (Serial.available() > 0) {
        int ibuf = 0;
        int incoming = 0;

        while (incoming != '\n' && ibuf < BUFSIZE)
            buffer[ibuf++] = Serial.read();
        
        if (ibuf == BUFSIZE) {
            buffer[BUFSIZE-1] = '\0';
            Serial.print("error \"oversized message\" ");
            Serial.println(buffer);
        }
        else {
            pending = 1;
        }
    }


    return pending;
}

void loop() {

    checkDoor();
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

#define INPUT(S) (strcmp((S), buffer) == 0)

    if (checkSerialCommand()) {
        if (INPUT("temperature")) {
            float temp = readTemperature(tempPin);
            Serial.print("temperature ");
            Serial.print(temp);
            Serial.println('C');
        }
    }
}

