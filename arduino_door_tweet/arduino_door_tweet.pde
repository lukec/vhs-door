/* Door Tweet
   gang programmed by VHS (c) copyright 2009.
   goldfish vanjuggler tristan
   see LICENSE file for full details.
*/

#define doorPin (4)

int doorPinState;

void setup() {
    Serial.begin( 9600 );
    pinMode( doorPin, INPUT );
    digitalWrite( doorPin, HIGH ); 
    doorPinState = digitalRead( doorPin );
}

void loop() {
    int newDoorPinState;
    newDoorPinState = digitalRead( doorPin );
    if( doorPinState != newDoorPinState ){
        doorPinState = newDoorPinState;
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
}

