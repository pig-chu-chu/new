using UnityEngine;
using System;

[RequireComponent(typeof(Rigidbody), typeof(SphereCollider))]
public class BallEvents : MonoBehaviour
{
    [Header("State")]
    public Rigidbody rb;
    public Transform owner;  // 誰現在持球（手）

    // 事件：外部可以訂閱
    public event Action<Transform> OnCatch;

    void Reset()
    {
        rb = GetComponent<Rigidbody>();
    }

    // 被手呼叫：接球
    public void Catch(Transform hand)
    {
        owner = hand;
        rb.isKinematic = true;
        rb.velocity = Vector3.zero;

        Debug.Log($"[BallEvents] Catch by {hand.name}");
        OnCatch?.Invoke(hand);
    }

    // 被手呼叫：放球
    public void Release(Vector3 velocity)
    {
        owner = null;
        rb.isKinematic = false;
        rb.velocity = velocity;
    }
}
