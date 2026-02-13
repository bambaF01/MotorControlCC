// ================== 1 MOTEUR + 1 ENCODEUR (Arduino Due) ==================

// ----- SERIAL & PWM SETTINGS -----
#if defined(ARDUINO_SAM_DUE)
// Mettre a 1 si tu utilises le port USB natif (SerialUSB).
#define USE_SERIAL_USB 0
const uint16_t PWM_MAX = 4095; // 12-bit PWM on Due
#if USE_SERIAL_USB
#define SERIAL_IF SerialUSB
#else
#define SERIAL_IF Serial
#endif
#else
const uint16_t PWM_MAX = 255;
#define SERIAL_IF Serial
#endif

// ----- ENCODEURS -----
// A doit etre sur D2 ou D3 (interruptions). B peut etre sur n'importe quelle pin digitale.
const int encA = 2; // A (INT0)
const int encB = 7; // B

// FIT0450 : 11 impulsions / tour moteur (sur A en RISING)
const int ENC_CPR = 11;

const unsigned long periodeMesure = 100; // ms

volatile long count = 0;
unsigned long tPrev = 0;
float rpm = 0.0f;

// ----- DRIVER MOTEUR (DRV8871 en mode XOR) -----
// D'apres le schema: PWM1 -> D9, PWM2 -> D6
const int pwmPin1 = 9; // PWM1
const int pwmPin2 = 6; // PWM2

int pwmCmd = 0; // 0..PWM_MAX
int sens = 1;    // 1 = avant, -1 = arriere

// ----- BOUCLE OUVERTE -----
int targetPwm = 0;

// ------------------ INTERRUPTIONS ENCODEURS ------------------
void isr() {
 if (digitalRead(encB) == HIGH) count++;
 else count--;
}

// ------------------ FONCTIONS MOTEUR ------------------
void setMotor(int pwmVal, int direction) {
 pwmVal = constrain(pwmVal, 0, PWM_MAX);
 // DRV8871 XOR: un PWM a 100%, l'autre a (100% - consigne)
 if (direction >= 0) {
  analogWrite(pwmPin1, PWM_MAX);
  analogWrite(pwmPin2, PWM_MAX - pwmVal);
 } else {
  analogWrite(pwmPin1, PWM_MAX - pwmVal);
  analogWrite(pwmPin2, PWM_MAX);
 }
}

void stopMotors() {
 analogWrite(pwmPin1, 0);
 analogWrite(pwmPin2, 0);
}

// ------------------ SETUP ------------------
void setup() {
 SERIAL_IF.begin(9600);
#if defined(ARDUINO_SAM_DUE)
 analogWriteResolution(12);
#endif

 pinMode(encA, INPUT_PULLUP);
 pinMode(encB, INPUT_PULLUP);

 pinMode(pwmPin1, OUTPUT);
 pinMode(pwmPin2, OUTPUT);

 attachInterrupt(digitalPinToInterrupt(encA), isr, RISING);

 tPrev = millis();

 setMotor(pwmCmd, sens);

 SERIAL_IF.println("Mode boucle ouverte");
 SERIAL_IF.print("Cmd: pXXX (pwm 0..");
 SERIAL_IF.print(PWM_MAX);
 SERIAL_IF.println("), s stop");
}

// ------------------ LOOP ------------------
void loop() {
 if (SERIAL_IF.available()) {
  char c = SERIAL_IF.read();

  if (c == 's') { stopMotors(); }
  if (c == 'p') { // ex: p120 (pwm consigne moteur gauche)
   int val = SERIAL_IF.parseInt();
   val = constrain(val, 0, PWM_MAX);
   targetPwm = val;
   if (val == 0) {
    pwmCmd = 0;
    stopMotors();
   }
  }
 }

 unsigned long t = millis();
 if (t - tPrev >= periodeMesure) {
  noInterrupts();
  long imp = count; count = 0;
  interrupts();

  float tours = (float)imp / ENC_CPR;
  float dtMs = (float)(t - tPrev);
  rpm = (tours * 600.0f) / dtMs;

  pwmCmd = targetPwm;
  if (pwmCmd == 0) {
   stopMotors();
  } else {
   setMotor(pwmCmd, sens);
  }

  // Serial Plotter: courbes rpm + pwm uniquement
  SERIAL_IF.print("rpm:");
  SERIAL_IF.print(rpm);
  SERIAL_IF.print(" pwm:");
  SERIAL_IF.println(targetPwm);

  tPrev = t;
 }
}
