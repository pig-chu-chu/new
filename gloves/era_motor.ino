#include <ESP32Servo.h>
#include "BluetoothSerial.h"
#define VIBE_NUM 14
BluetoothSerial SerialBT;
unsigned long vibeStartTime[VIBE_NUM] = { 0 };
bool vibeActive[VIBE_NUM] = { false };
const unsigned long VIBE_DURATION = 300;  // 持續時間0.5秒(毫秒)
// 震動馬達腳位，依實際硬體接法修改，請確保硬體接線對應
//int vibePins[VIBE_NUM] = {17, 5, 18, 19, 21, 22, 23, 16, 33, 32, 35, 34, 39, 36, 25, 26, 27, 14, 12, 13};
int vibePins[VIBE_NUM] = {17, 5, 18, 19, 21, 22, 23,16,13,12,14,27,26,25};
// 存放震動馬達狀態（0關，255開）
int vibeStates[VIBE_NUM] = { 0 };
// 目前控制模式
// true: 用PC Serial指令控制手指與震動
// false: 用電位器模擬手指彎曲；震動維持最後指令
bool serialControlMode = true;
void setup() {
  Serial.begin(115200);
  SerialBT.begin("GloveController");
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
  int vidx = cmd.indexOf("VIBE:");
  if (vidx != -1) {
    String vibes = cmd.substring(vidx + 5);
    for (int i = 0; i < VIBE_NUM; i++) {
      int comma = vibes.indexOf(',');
      int val;
      if (comma == -1) {
        val = vibes.toInt();
        vibes = "";
      } else {
        val = vibes.substring(0, comma).toInt();
        vibes = vibes.substring(comma + 1);
      }
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
