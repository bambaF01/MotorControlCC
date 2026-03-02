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
const int MAX_RPM = 60;

volatile long count = 0;
unsigned long tPrev = 0;
float rpm = 0.0f;

// ----- DRIVER MOTEUR (DRV8871 en mode XOR) -----
// D'apres le schema: PWM1 -> D9, PWM2 -> D6
const int pwmPin1 = 9; // PWM1
const int pwmPin2 = 6; // PWM2

int pwmCmd = 200; // 0..PWM_MAX
int sens = 1;    // 1 = avant, -1 = arriere

// ----- PID VITESSE -----
const bool usePid = true;
float targetRpm = 0.0f;

// Gains PID (a regler)
float Kp = 28.6f;
float Ki = 40.0f;
float Kd = 0.0f;

float iTerm = 0.0f;
float prevErr = 0.0f;

const float iClamp = 200.0f;
const float KP_STEP = 0.1f;
const float KI_STEP = 0.1f;
const float KD_STEP = 0.1f;
bool readLine(String &out) {
 static String buf;
 while (SERIAL_IF.available()) {
  char c = (char)SERIAL_IF.read();
  if (c == '\r') continue;
  if (c == '\n') {
   out = buf;
   buf = "";
   return true;
  }
  buf += c;
 }
 return false;
}

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

int pidStep(float targetRpm, float measRpm, float dtSec, float &iTerm, float &prevErr,
      float Kp, float Ki, float Kd) {
 float err = targetRpm - measRpm;
 iTerm += err * dtSec;
 iTerm = constrain(iTerm, -iClamp, iClamp);
 float dErr = (dtSec > 0.0f) ? (err - prevErr) / dtSec : 0.0f;
 prevErr = err;
 float out = (Kp * err) + (Ki * iTerm) + (Kd * dErr);
 int pwm = (int)constrain(out, 0.0f, (float)PWM_MAX);
 return pwm;
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

 SERIAL_IF.println("Tape h pour l'aide.");
}

// ------------------ LOOP ------------------
void loop() {
 String line;
 if (readLine(line)) {
  line.trim();
  if (line.length() == 0) {
   // ignore empty
  } else if (line == "h" || line == "help" || line == "?") {
   SERIAL_IF.println("=== MENU COMMANDES ===");
   SERIAL_IF.println("h / help / ?   : afficher ce menu");
   SERIAL_IF.println("vXXX           : consigne vitesse en rpm (ex: v120)");
   SERIAL_IF.println("s              : stop moteur");
   SERIAL_IF.println("kpX            : set Kp (ex: kp0.12)");
   SERIAL_IF.println("kiX            : set Ki (ex: ki0.03)");
   SERIAL_IF.println("kdX            : set Kd (ex: kd0.00)");
   SERIAL_IF.println("kp+ / kp-      : increment/decrement Kp");
   SERIAL_IF.println("ki+ / ki-      : increment/decrement Ki");
   SERIAL_IF.println("kd+ / kd-      : increment/decrement Kd");
   SERIAL_IF.println("g              : affiche Kp/Ki/Kd");
  } else if (line == "g") {
   SERIAL_IF.print("Kp=");
   SERIAL_IF.print(Kp);
   SERIAL_IF.print(" Ki=");
   SERIAL_IF.print(Ki);
   SERIAL_IF.print(" Kd=");
   SERIAL_IF.println(Kd);
  } else if (line == "s") {
   stopMotors();
  } else if (line.startsWith("v")) { // ex: v120 (rpm consigne pour les deux)
   int val = line.substring(1).toInt();
   val = constrain(val, 0, MAX_RPM);
   if (val == 0) {
    targetRpm = 0.0f;
    iTerm = 0.0f;
    prevErr = 0.0f;
    pwmCmd = 0;
    stopMotors();
//    seqActive = false;
   } else {
    targetRpm = val;
   }
  } else if (line == "kp+") {
   Kp = max(0.0f, Kp + KP_STEP);
   SERIAL_IF.print("Kp=");
   SERIAL_IF.println(Kp);
  } else if (line == "kp-") {
   Kp = max(0.0f, Kp - KP_STEP);
   SERIAL_IF.print("Kp=");
   SERIAL_IF.println(Kp);
  } else if (line == "ki+") {
   Ki = max(0.0f, Ki + KI_STEP);
   SERIAL_IF.print("Ki=");
   SERIAL_IF.println(Ki);
  } else if (line == "ki-") {
   Ki = max(0.0f, Ki - KI_STEP);
   SERIAL_IF.print("Ki=");
   SERIAL_IF.println(Ki);
  } else if (line == "kd+") {
   Kd = max(0.0f, Kd + KD_STEP);
   SERIAL_IF.print("Kd=");
   SERIAL_IF.println(Kd);
  } else if (line == "kd-") {
   Kd = max(0.0f, Kd - KD_STEP);
   SERIAL_IF.print("Kd=");
   SERIAL_IF.println(Kd);
  } else if (line.startsWith("kp")) {
   Kp = max(0.0f, line.substring(2).toFloat());
   SERIAL_IF.print("Kp=");
   SERIAL_IF.println(Kp);
  } else if (line.startsWith("ki")) {
   Ki = max(0.0f, line.substring(2).toFloat());
   SERIAL_IF.print("Ki=");
   SERIAL_IF.println(Ki);
  } else if (line.startsWith("kd")) {
   Kd = max(0.0f, line.substring(2).toFloat());
   SERIAL_IF.print("Kd=");
   SERIAL_IF.println(Kd);
  }
 }

 unsigned long t = millis();
 if (t - tPrev >= periodeMesure) {
  noInterrupts();
  long imp = count; count = 0;
  interrupts();

  float tours = (float)imp / ENC_CPR;
  float dtMs = (float)(t - tPrev);
  float dtSec = dtMs / 1000.0f;
  rpm = (tours * 600.0f) / dtMs;

  if (usePid) {
   float meas = fabs(rpm);
   pwmCmd = pidStep(targetRpm, meas, dtSec, iTerm, prevErr, Kp, Ki, Kd);
   setMotor(pwmCmd, sens);
  }

  // Serial Plotter: courbes rpm + consigne uniquement
  SERIAL_IF.print("rpm:");
  SERIAL_IF.print(rpm);
  SERIAL_IF.print(" cons:");
  SERIAL_IF.println(targetRpm);

  tPrev = t;
 }
}
