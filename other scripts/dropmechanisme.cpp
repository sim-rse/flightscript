// trigger naar beneden: output 2000
// trigger naar midden: output 1500
// trigger naar boven: output 980
// droppen = trigger B naar beneden (2000)
// laden = trigger B naar boven (980)


#include <Servo.h>
Servo droneteam;


int value = 0;

const int servoPin = 3;
const int schakelaarPin = 2;

long vaccin_1 = 80;
long vaccin_2 = 0;
long vaccin_3 = 135;
long gesloten = 100;

bool switchState = false;
bool check_inladen = false;
bool check_uitladen_1 = false;
bool check_uitladen_2 = false;
bool check_uitladen_3 = false;

long delayTime_schakelaar = 25;
long delayTime_inladen = 3500;
long delayTime_uitladen_1 = 50;
long delayTime_uitladen_2 = 50;
long delayTime_uitladen_3 = 50;

unsigned long pulseWidth_nieuw = 0;
unsigned long pulseWidth_oud = 0;

void setup() {

  Serial.begin(9600);
  pinMode(schakelaarPin, INPUT);
  droneteam.attach(servoPin);
  droneteam.write(gesloten);

}

void loop() {

  pulseWidth_oud = pulseWidth_nieuw;
  Serial.print("pulseWidth_oud = ");
  Serial.println(pulseWidth_oud);
  pulseWidth_nieuw = pulseIn(schakelaarPin, HIGH);
  Serial.print("pulseWidth_nieuw = ");
  Serial.println(pulseWidth_nieuw);

  if (abs(pulseWidth_nieuw - pulseWidth_oud) > 200) {
    switchState = true;
  }
  else {
    switchState = false;
  }

  if (switchState) {

    if (pulseWidth_nieuw < 1250) {
      Serial.println("Laden!");
      droneteam.write(gesloten);
      delay(delayTime_inladen);

      droneteam.write(vaccin_1);
      delay(delayTime_inladen);

      droneteam.write(vaccin_2);
      delay(delayTime_inladen);
      
      droneteam.write(vaccin_3);
      delay(delayTime_inladen);

      droneteam.write(gesloten);

      check_uitladen_1 = false;
      check_uitladen_2 = false;
      check_uitladen_3 = false;
    }

    else if (pulseWidth_nieuw > 1750) {
      if (!check_uitladen_1) {
        Serial.println("Uitladen 1!");
        droneteam.write(vaccin_1);
        delay(delayTime_uitladen_1);
        check_uitladen_1 = true;
      }

      else if (!check_uitladen_2) {
        Serial.println("Uitladen 2!");
        droneteam.write(vaccin_2);
        delay(delayTime_uitladen_2);
        check_uitladen_2 = true;
      }

      else if (!check_uitladen_3) {
        Serial.println("Uitladen 3!");
        droneteam.write(vaccin_3);
        delay(delayTime_uitladen_3);
        check_uitladen_3 = true;
      }
    }
  }
}
