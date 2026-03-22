namespace ProcessDsl.EntityValidation.Models;

public class EntityValidationConfiguration
{
    /// <summary>
    /// Base directory for OpenAPI contract files.
    /// Defaults to "openAPI_contracts" relative to the application directory.
    /// </summary>
    public string ContractsBaseDir { get; set; } = "openAPI_contracts";

    /// <summary>
    /// Zeebe gRPC gateway address (e.g., localhost:26500)
    /// </summary>
    public string GatewayAddress { get; set; } = "localhost:26500";

    /// <summary>
    /// Use plaintext connection (no TLS) - for local development
    /// </summary>
    public bool UsePlainText { get; set; } = true;

    /// <summary>
    /// Optional authentication token for Camunda Cloud
    /// </summary>
    public string? AuthToken { get; set; }
}
