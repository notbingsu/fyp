using System;
using System.Text;
using UnityEngine;
using NativeWebSocket;

/// <summary>
/// Manages the WebSocket connection to the haptic experiment server.
/// Attach to the same GameObject as TrainingManager.
/// Requires: NativeWebSocket (https://github.com/endel/NativeWebSocket)
/// </summary>
public class HapticServerClient : MonoBehaviour
{
    public static HapticServerClient Instance;

    [Header("Server")]
    public string serverUrl = "ws://localhost:5001";

    [Header("Haptic Parameters")]
    [Range(0.01f, 0.5f)] public float k_xy = 0.06f;
    [Range(0.05f, 0.5f)] public float k_z  = 0.15f;

    private WebSocket _ws;
    public string LastRunId { get; private set; }
    public bool IsConnected => _ws != null && _ws.State == WebSocketState.Open;

    void Awake()
    {
        Instance = this;
    }

    async void Start()
    {
        await Connect();
    }

    public async System.Threading.Tasks.Task Connect()
    {
        _ws = new WebSocket(serverUrl);

        _ws.OnOpen += () =>
            Debug.Log("[HapticServerClient] Connected to " + serverUrl);

        _ws.OnMessage += (bytes) =>
        {
            string json = Encoding.UTF8.GetString(bytes);
            Debug.Log("[HapticServerClient] ← " + json);
            HandleMessage(json);
        };

        _ws.OnError += (e) =>
            Debug.LogError("[HapticServerClient] Error: " + e);

        _ws.OnClose += (code) =>
            Debug.Log("[HapticServerClient] Disconnected: " + code);

        await _ws.Connect();
    }

    // Must be called every frame so NativeWebSocket can dispatch messages on the main thread
    void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        _ws?.DispatchMessageQueue();
#endif
    }

    // ---------------------------------------------------------------
    // Public API — called by TrainingManager
    // ---------------------------------------------------------------

    public async void SendStart(string participantId, string scenario, bool hapticEnabled)
    {
        if (!IsConnected)
        {
            Debug.LogWarning("[HapticServerClient] Not connected — cannot send start.");
            return;
        }

        var payload = new StartPayload
        {
            action      = "start",
            participant = participantId,
            scenario    = scenario,
            haptic      = hapticEnabled,
            k_xy        = this.k_xy,
            k_z         = this.k_z
        };

        string json = JsonUtility.ToJson(payload);
        Debug.Log("[HapticServerClient] → " + json);
        await _ws.SendText(json);
    }

    public async void SendStop()
    {
        if (!IsConnected)
        {
            Debug.LogWarning("[HapticServerClient] Not connected — cannot send stop.");
            return;
        }

        string json = "{\"action\":\"stop\"}";
        Debug.Log("[HapticServerClient] → " + json);
        await _ws.SendText(json);
    }

    // ---------------------------------------------------------------
    // Message handling
    // ---------------------------------------------------------------

    private void HandleMessage(string json)
    {
        var msg = JsonUtility.FromJson<ServerMessage>(json);

        switch (msg.status)
        {
            case "started":
                LastRunId = msg.run_id;
                Debug.Log("[HapticServerClient] Experiment started. run_id=" + LastRunId);
                break;

            case "completed":
                Debug.Log("[HapticServerClient] Experiment completed. run_id=" + msg.run_id);
                break;

            case "failed":
                Debug.LogError("[HapticServerClient] Experiment failed: " + msg.error);
                break;

            case "error":
                Debug.LogError("[HapticServerClient] Server error: " + msg.error);
                break;
        }
    }

    async void OnApplicationQuit()
    {
        if (_ws != null)
            await _ws.Close();
    }

    // ---------------------------------------------------------------
    // JSON-serialisable types
    // ---------------------------------------------------------------

    [Serializable]
    private class StartPayload
    {
        public string action;
        public string participant;
        public string scenario;
        public bool   haptic;
        public float  k_xy;
        public float  k_z;
    }

    [Serializable]
    private class ServerMessage
    {
        public string status;
        public string run_id;
        public string error;
    }
}
