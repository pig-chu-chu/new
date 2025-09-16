#include <ESP32Servo.h>
#include "BluetoothSerial.h"
#define VIBE_NUM 6
#define FINGER_NUM 5
BluetoothSerial SerialBT;
unsigned long vibeStartTime[VIBE_NUM] = { 0 };
bool vibeActive[VIBE_NUM] = { false };
const unsigned long VIBE_DURATION = 300;  // 持續時間0.5秒(毫秒)
// 伺服馬達腳位，依實際硬體接法修改
int fingerServoPins[FINGER_NUM] = { 18, 23, 22, 21, 19 };
Servo fingerServos[FINGER_NUM];
// 震動馬達腳位，依實際硬體接法修改，請確保硬體接線對應
int vibePins[VIBE_NUM] = {25,26,27,14,12,13,};
int vibeStates[VIBE_NUM] = { 0 };
// 目前控制模式
// true: 用PC Serial指令控制手指與震動
// false: 用電位器模擬手指彎曲；震動維持最後指令
bool serialControlMode = true;
void setup() {
  Serial.begin(115200);
  SerialBT.begin("GloveController");
  for (int i = 0; i < FINGER_NUM; i++) {
    fingerServos[i].attach(fingerServoPins[i]);
    fingerServos[i].write(0);
  }
  for (int i = 0; i < VIBE_NUM; i++) {
    pinMode(vibePins[i], OUTPUT);  // 初始關閉
    digitalWrite(vibePins[i], LOW);
  }
  Serial.println("ESP32 Servo+Vibration Controller ready");
}
void loop() {
  // USB
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    serialHandler(msg);
  }
  // 藍牙
  if (SerialBT.available()) {
    String msg = SerialBT.readStringUntil('\n');
    serialHandler(msg);
  }
  unsigned long currentMillis = millis();
  for (int i = 0; i < VIBE_NUM; i++) {
    if (vibeActive[i]) {
      if (currentMillis - vibeStartTime[i] >= VIBE_DURATION) {
        digitalWrite(vibePins[i], LOW);
        vibeActive[i] = false;
      }
    }
  }
}
void serialHandler(String cmd) {
  cmd.trim();
  // FINGERS:90,60,120,80,100;VIBE:255,255,0,0,...
  int fidx = cmd.indexOf("FINGERS:");
  int vidx = cmd.indexOf("VIBE:");
  // 解析手指
  if (fidx != -1) {
    int fend = cmd.indexOf(';', fidx);
    String fingstr = cmd.substring(fidx + 8, fend);
    int s = 0;
    for (int i = 0; i < FINGER_NUM; i++) {
      int comma = fingstr.indexOf(',');
      int ang;
      if (comma == -1) {
        ang = fingstr.toInt();
        fingstr = "";
      } else {
        ang = fingstr.substring(0, comma).toInt();
        fingstr = fingstr.substring(comma + 1);
      }
      ang = constrain(ang, 0, 180);
      fingerServos[i].write(ang);
    }
  }
if (vidx != -1) {
  String vibes = cmd.substring(vidx + 5);  
  if (vibes.length() && vibes.charAt(vibes.length() - 1) == ';') {
    vibes.remove(vibes.length() - 1);
  }

  int vals[6] = {0, 0, 0, 0, 0, 0};   // 存放最後 6 筆
  int end = vibes.length();

  // 從尾端往前回溯，擷取最後 6 段
  for (int k = 5; k >= 0; --k) {
    int comma = vibes.lastIndexOf(',', end - 1);
    String token = (comma == -1) ? vibes.substring(0, end)
                                 : vibes.substring(comma + 1, end);
    token.trim();
    vals[k] = token.toInt();
    if (comma == -1) break;   // 已到最前段
    end = comma;              // 向前移動終點
  }

  for (int i = 0; i < VIBE_NUM; i++) {
    int val = vals[i];
    if (val > 0) {
      digitalWrite(vibePins[i], HIGH);
      vibeStartTime[i] = millis();
      vibeActive[i] = true;
    } else {
      digitalWrite(vibePins[i], LOW);
      vibeActive[i] = false;
    }
  }
}

}
