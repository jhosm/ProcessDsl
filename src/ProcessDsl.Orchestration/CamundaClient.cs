using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using ProcessDsl.Orchestration.Models;
using Zeebe.Client.Api.Responses;
using Zeebe.Client;

namespace ProcessDsl.Orchestration;

/// <summary>
/// Implementation of Camunda Zeebe gRPC client
/// </summary>
public class CamundaClient : ICamundaClient, IDisposable
{
    private readonly IZeebeClient _zeebeClient;
    private readonly CamundaConfiguration _config;

    public CamundaClient(IOptions<CamundaConfiguration> config)
    {
        _config = config?.Value ?? throw new ArgumentNullException(nameof(config));

        // Build Zeebe gRPC client
        if (_config.UsePlainText)
        {
            // Local development - plaintext without authentication
            _zeebeClient = ZeebeClient.Builder()
                .UseGatewayAddress(_config.GatewayAddress)
                .UsePlainText()
                .Build();
        }
        else
        {
            // Production - TLS with authentication
            if (string.IsNullOrEmpty(_config.AuthToken))
            {
                throw new InvalidOperationException(
                    "AuthToken is required when UsePlainText is false");
            }

            _zeebeClient = ZeebeClient.Builder()
                .UseGatewayAddress(_config.GatewayAddress)
                .UseTransportEncryption()
                .UseAccessToken(_config.AuthToken)
                .Build();
        }
    }

    /// <inheritdoc />
    public async Task<ProcessInstance> CreateProcessInstanceAsync(
        string processDefinitionKey,
        StartProcessRequest request,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(processDefinitionKey))
            throw new ArgumentException("Process definition key cannot be empty", nameof(processDefinitionKey));

        if (request == null)
            throw new ArgumentNullException(nameof(request));

        try
        {
            // Build Zeebe process instance creation request
            var createRequest = _zeebeClient.NewCreateProcessInstanceCommand()
                .BpmnProcessId(processDefinitionKey)
                .LatestVersion();

            // Add variables - serialize all variables as a single JSON object
            if (request.Variables.Any())
            {
                var variablesJson = JsonConvert.SerializeObject(request.Variables);
                createRequest = createRequest.Variables(variablesJson);
            }

            // Send request to Zeebe
            var response = await createRequest.Send(cancellationToken);

            return new ProcessInstance
            {
                ProcessInstanceKey = response.ProcessInstanceKey,
                ProcessDefinitionKey = response.ProcessDefinitionKey,
                BpmnProcessId = response.BpmnProcessId,
                Version = response.Version
            };
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException(
                $"Failed to start process '{processDefinitionKey}': {ex.Message}", ex);
        }
    }

    /// <inheritdoc />
    public async Task<ProcessInstance> CreateProcessInstanceWithEntityAsync(
        string processDefinitionKey,
        object entityData,
        CancellationToken cancellationToken = default)
    {
        var request = new StartProcessRequest
        {
            Variables = new Dictionary<string, object>
            {
                ["processEntity"] = entityData
            }
        };

        return await CreateProcessInstanceAsync(processDefinitionKey, request, cancellationToken);
    }

    public void Dispose()
    {
        _zeebeClient?.Dispose();
    }
}
