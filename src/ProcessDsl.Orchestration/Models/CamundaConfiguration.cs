namespace ProcessDsl.Orchestration.Models;

/// <summary>
/// Configuration options for Camunda Zeebe connection
/// </summary>
public class CamundaConfiguration
{
    /// <summary>
    /// Zeebe gRPC gateway address (e.g., localhost:26500)
    /// </summary>
    public string GatewayAddress { get; set; } = "localhost:26500";

    /// <summary>
    /// Optional authentication token for Camunda Cloud
    /// </summary>
    public string? AuthToken { get; set; }

    /// <summary>
    /// Request timeout in seconds (default: 30)
    /// </summary>
    public int TimeoutSeconds { get; set; } = 30;

    /// <summary>
    /// Use plaintext connection (no TLS) - for local development
    /// </summary>
    public bool UsePlainText { get; set; } = true;

    /// <summary>
    /// Keep alive time in seconds for gRPC connection (default: 30)
    /// </summary>
    public int KeepAliveSeconds { get; set; } = 30;
}
