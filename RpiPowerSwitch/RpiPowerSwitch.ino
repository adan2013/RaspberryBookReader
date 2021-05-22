#define BTN_PIN 0
#define LED_PIN 1
#define RPI_IN_PIN 2
#define RPI_OUT_PIN 3
#define MOSFET_PIN 4
#define PWR_TIMEOUT 30000
#define BLINK_FREQ 500

#define S_OFF 0
#define S_PRESSED_PWR_ON 1
#define S_TURNING_ON 2
#define S_ON 3
#define S_PRESSED_PWR_OFF 4
#define S_TURNING_OFF 5

#define LED_OFF 0
#define LED_ON 1
#define LED_BLINK 2

byte state = S_OFF;
byte ledState = LED_OFF;
bool blinkLedOn = false;
unsigned long lastStateSwitchTime = 0;
unsigned long lastBlinkSwitchTime = 0;

bool timeoutFunction(unsigned long eventTime, unsigned long timeoutValue) {
  return millis() - eventTime >= timeoutValue;
}

bool buttonIsPressed() {
  return digitalRead(BTN_PIN) == LOW;
}

bool rpiSignalIsLow() {
  return digitalRead(RPI_IN_PIN) == LOW;
}

void switchOutputs(byte led, bool rpi, bool mosfet) {
  ledState = led;
  blinkLedOn = true;
  lastBlinkSwitchTime = millis();
  digitalWrite(LED_PIN, led == LED_OFF ? LOW : HIGH);
  digitalWrite(RPI_OUT_PIN, rpi ? HIGH : LOW);
  digitalWrite(MOSFET_PIN, mosfet ? HIGH : LOW);
}

void setup() {
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  pinMode(RPI_IN_PIN, INPUT_PULLUP);
  pinMode(RPI_OUT_PIN, OUTPUT);
  pinMode(MOSFET_PIN, OUTPUT);
  switchOutputs(LED_ON, false, false);
  delay(300);
  switchOutputs(LED_OFF, false, false);
}

void switchState(int newState) {
  state = newState;
  lastStateSwitchTime = millis();
  switch(state) {
    case S_OFF: switchOutputs(LED_OFF, false, false); break;
    case S_PRESSED_PWR_ON: switchOutputs(LED_OFF, false, false); break;
    case S_TURNING_ON: switchOutputs(LED_BLINK, true, true); break;
    case S_ON: switchOutputs(LED_ON, true, true); break;
    case S_PRESSED_PWR_OFF: switchOutputs(LED_ON, true, true); break;
    case S_TURNING_OFF: switchOutputs(LED_BLINK, false, true); break;
  }
}

void loop() {
  switch(state) {
    case S_OFF:
      if(buttonIsPressed()) switchState(S_PRESSED_PWR_ON);
      break;
    case S_PRESSED_PWR_ON:
      if(!buttonIsPressed()) switchState(S_TURNING_ON);
      break;
    case S_TURNING_ON:
      if(rpiSignalIsLow()) switchState(S_ON);
      break;
    case S_ON:
      if(buttonIsPressed()) switchState(S_PRESSED_PWR_OFF);
      break;
    case S_PRESSED_PWR_OFF:
      if(!buttonIsPressed()) switchState(S_TURNING_OFF);
      break;
    case S_TURNING_OFF:
      if(timeoutFunction(lastStateSwitchTime, PWR_TIMEOUT)) switchState(S_OFF);
      break;
  }
  if(ledState == LED_BLINK && timeoutFunction(lastBlinkSwitchTime, BLINK_FREQ)) {
    blinkLedOn = !blinkLedOn;
    lastBlinkSwitchTime = millis();
    digitalWrite(LED_PIN, blinkLedOn ? HIGH : LOW);
  }
}
