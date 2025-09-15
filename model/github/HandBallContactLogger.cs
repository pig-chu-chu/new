using UnityEngine;

[RequireComponent(typeof(Collider)), RequireComponent(typeof(Rigidbody))]
public class HandBallContactLogger : MonoBehaviour
{
    [Header("Ball Target")]
    public Collider ballCollider;              // 指到「真正的球」的 SphereCollider（Rigidbody 那顆）

    [Header("Debounce / Grace")]
    [Tooltip("離開後需連續多久都未重疊，才判定真正放開（秒）")]
    public float releaseGrace = 0.25f;
    [Tooltip("兩碰撞體最近點距離超過此值才視為明確分離（公尺），避免邊界貼合抖動")]
    public float minSeparation = 0.005f;

    bool   inContact = false;                  // 目前是否視為接觸中
    bool   exitPending = false;                // 已經偵測到離開，等待緩衝確認
    float  firstContactT = -1f;                // 首次接觸時間
    float  exitStartT = -1f;                   // 開始判定離開的時間

    Collider handCol;

    void Awake()
    {
        handCol = GetComponent<Collider>();
        handCol.isTrigger = true;

        var rb = GetComponent<Rigidbody>();
        rb.isKinematic = true; // 手的 Trigger 用 Kinematic RB

        Debug.Log($"[HB] TIMER START t={Time.time:F3}s (Play pressed)");
    }

    void Start()
    {
        // 若一開始就重疊，直接視為已接觸（拿球）
        if (ballCollider && OverlappingOrVeryClose())
            BeginContact(initial:true);
    }

    void OnTriggerEnter(Collider other)
    {
        if (other != ballCollider) return;

        // 任何重新重疊都取消「離開待確認」
        if (exitPending)
        {
            exitPending = false;
            exitStartT = -1f;
        }

        if (!inContact)
            BeginContact(initial:false);
    }

    void OnTriggerExit(Collider other)
    {
        if (other != ballCollider) return;
        if (!inContact || exitPending) return;

        // 不立即算放開，先進入緩衝期
        exitPending = true;
        exitStartT = Time.time;
    }

    void Update()
    {
        if (!exitPending || ballCollider == null) return;

        // 在緩衝期內，只要又靠得很近或重疊，就取消放開
        if (OverlappingOrVeryClose())
        {
            exitPending = false;
            exitStartT = -1f;
            return;
        }

        // 維持明確分離超過 releaseGrace，才算真正放開
        if (Time.time - exitStartT >= releaseGrace)
        {
            EndContact();
            exitPending = false;
            exitStartT = -1f;
        }
    }

    // ===== helpers =====
    void BeginContact(bool initial)
    {
        inContact = true;
        exitPending = false;
        exitStartT = -1f;

        if (firstContactT < 0f)
        {
            firstContactT = Time.time;
            Debug.Log($"[HB] HAND TOUCH BALL at t={firstContactT:F3}s" + (initial ? " (initial overlap)" : ""));
        }
        // 若你想每次重新接觸都當作新「開始」，把上面 if 改成：firstContactT = Time.time;
    }

    void EndContact()
    {
        if (!inContact) return;
        inContact = false;

        float endT = Time.time;
        float duration = (firstContactT >= 0f) ? (endT - firstContactT) : -1f;
        Debug.Log($"[HB] HAND RELEASE BALL at t={endT:F3}s (total hold {duration:F3}s)");

        // 若只要記錄一次完整拿球→放球，可在這裡重置 firstContactT = -1f;
        firstContactT = -1f;
    }

    bool OverlappingOrVeryClose()
    {
        // 1) 幾何重疊檢測（最可靠）
        Vector3 dir; float dist;
        bool penetrating = Physics.ComputePenetration(
            handCol, handCol.transform.position, handCol.transform.rotation,
            ballCollider, ballCollider.transform.position, ballCollider.transform.rotation,
            out dir, out dist);

        if (penetrating) return true;

        // 2) 沒穿透，再看最近點距離是否小於門檻（避免邊界貼合抖動）
        Vector3 pA = handCol.ClosestPoint(ballCollider.transform.position);
        Vector3 pB = ballCollider.ClosestPoint(handCol.transform.position);
        float d = Vector3.Distance(pA, pB);
        return d < minSeparation;
    }
}
