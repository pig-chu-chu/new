#include <Servo.h>

// 定義直流馬達控制腳位
#define A_IA      5    // 馬達輸出 A 端子 IA
#define A_IB      6    // 馬達輸出 B 端子 IB
#define SERVO_PIN 9    // 舵機訊號腳位

// 事件結構：動作名稱與觸發時間
struct Event { 
    String action;    // 動作名稱
    int touchTime;    // 觸發時間（秒）
};

const int MAX_EVENTS = 30;       // 最多能儲存的事件數量
Event events[MAX_EVENTS];        // 事件緩存陣列
int eventCount = 0;              // 當前緩存事件數量
int currentIndex = 0;            // 正在處理的事件索引
bool executionEnabled = false;   // 是否允許執行事件
Servo myservo;                   // 舵機物件

void setup() {
    // 設定馬達控制腳位為輸出模式
    pinMode(A_IA, OUTPUT);
    pinMode(A_IB, OUTPUT);

    // 初始化舵機並設定到起始角度 0
    myservo.attach(SERVO_PIN);
    myservo.write(0);

    // 啟用序列通訊，與主機通訊鮑率 9600
    Serial.begin(9600);
    while (!Serial) { }          // 等待序列埠準備就緒
    Serial.println("UNO ready"); // 顯示準備完成訊息
}

void loop() {
    // 持續讀取序列指令、並在允許時執行事件
    readSerialCommands();
    if (executionEnabled) processEvents();
}

void readSerialCommands() {
    // 處理從電腦或主機傳來的序列指令
    while (Serial.available()) {
        String line = Serial.readStringUntil('\n'); // 讀取一行
        line.trim();                               // 去除空白
        Serial.print("RECV:"); Serial.println(line);

        // 開啟執行：重置索引與緩存
        if (line.equalsIgnoreCase("SWITCH_ON")) {
            executionEnabled = true;
            currentIndex = 0;
            eventCount = 0;
            Serial.println("EXECUTION ENABLED");
        }
        // 關閉執行
        else if (line.equalsIgnoreCase("SWITCH_OFF")) {
            executionEnabled = false;
            Serial.println("EXECUTION DISABLED");
        }
        // 接收到動作事件，存入緩存
        else {
            int sep = line.indexOf(':');          // 找到動作與時間分隔
            if (sep > 0 && eventCount < MAX_EVENTS) {
                String act = line.substring(0, sep);           // 取動作名稱
                int t = line.substring(sep + 1).toInt();       // 取觸發時間
                events[eventCount++] = {act, t};               // 儲存事件
                Serial.print("STORED EVENT:"); 
                Serial.print(act); 
                Serial.print("@"); 
                Serial.println(t);
            }
        }
    }
}

void processEvents() {
    // 若無事件或已處理完畢則直接返回
    if (currentIndex >= eventCount) return;

    // 取得下一個事件並執行
    Event &e = events[currentIndex++];
    Serial.print("TRIGGER:"); 
    Serial.print(e.action); 
    Serial.print("@"); 
    Serial.println(e.touchTime);
    executeAction(e.action);

    // 遇到結束動作後，自動關閉執行
    if (e.action.equalsIgnoreCase("end")) {
        executionEnabled = false;
        Serial.println("EXECUTION AUTO-DISABLED");
    }
}

void executeAction(const String &action) {
    // 根據不同動作呼叫對應的硬體控制函式
    if (action.equalsIgnoreCase("投球") || action.equalsIgnoreCase("SPIKE")) {
        runAttackMotor();    // 攻擊動作
    }
    else if (action.equalsIgnoreCase("start") || action.equalsIgnoreCase("end")) {
        runReadyMotor();     // 準備動作
    }
    else if (action.equalsIgnoreCase("RECEIVE")
          || action.equalsIgnoreCase("SET")
          || action.equalsIgnoreCase("SERVE")
          || action.equalsIgnoreCase("BLOCK")
          || action.equalsIgnoreCase("運球")) {
        runMAXMotor();       // 接發球、二傳、發球、攔網、運球動作
    }
}

// ===== 以下為各動作對應的硬體控制實作 =====

void runAttackMotor() {
    // 舵機旋轉到 90 度
    myservo.write(90);
    delay(500);
    // 啟動馬達向前運轉
    digitalWrite(A_IA, HIGH);
    digitalWrite(A_IB, LOW);
    delay(5000);
    // 停止馬達
    digitalWrite(A_IA, LOW);
    digitalWrite(A_IB, LOW);
    // 舵機復位
    myservo.write(0);
    delay(200);
}

void runReadyMotor() {
    // 舵機旋轉到 60 度
    myservo.write(60);
    delay(500);
    // 啟動馬達向前運轉
    digitalWrite(A_IA, HIGH);
    digitalWrite(A_IB, LOW);
    delay(5000);
    // 停止馬達
    digitalWrite(A_IA, LOW);
    digitalWrite(A_IB, LOW);
    // 舵機復位
    myservo.write(0);
    delay(200);
}

void runMAXMotor() {
    // 舵機旋轉到 180 度
    myservo.write(180);
    delay(500);
    // 啟動馬達向前運轉
    digitalWrite(A_IA, HIGH);
    digitalWrite(A_IB, LOW);
    delay(5000);
    // 停止馬達
    digitalWrite(A_IA, LOW);
    digitalWrite(A_IB, LOW);
    // 舵機復位
    myservo.write(0);
    delay(200);
}
