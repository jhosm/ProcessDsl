using Microsoft.Extensions.Logging;
using ProcessDsl.Orchestration.Models;

namespace ProcessDsl.Orchestration;

/// <summary>
/// Implementation of process orchestration for ProcessDsl workflows
/// </summary>
public class ProcessOrchestrator : IProcessOrchestrator
{
    private readonly ICamundaClient _camundaClient;
    private readonly ILogger<ProcessOrchestrator>? _logger;

    public ProcessOrchestrator(
        ICamundaClient camundaClient,
        ILogger<ProcessOrchestrator>? logger = null)
    {
        _camundaClient = camundaClient ?? throw new ArgumentNullException(nameof(camundaClient));
        _logger = logger;
    }

    /// <inheritdoc />
    public async Task<ProcessInstance> StartProcessForEntityAsync(
        string processId,
        object entityData,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(processId))
            throw new ArgumentException("Process ID cannot be empty", nameof(processId));

        if (entityData == null)
            throw new ArgumentNullException(nameof(entityData));

        _logger?.LogInformation(
            "Starting process '{ProcessId}' for entity type {EntityType}",
            processId,
            entityData.GetType().Name);

        try
        {
            var processInstance = await _camundaClient.CreateProcessInstanceWithEntityAsync(
                processId,
                entityData,
                cancellationToken);

            _logger?.LogInformation(
                "Successfully started process instance {ProcessInstanceKey} for process '{ProcessId}'",
                processInstance.ProcessInstanceKey,
                processId);

            return processInstance;
        }
        catch (Exception ex)
        {
            _logger?.LogError(
                ex,
                "Failed to start process '{ProcessId}' for entity",
                processId);
            throw;
        }
    }

    /// <inheritdoc />
    public async Task<ProcessInstance> StartProcessAsync(
        string processId,
        Dictionary<string, object> variables,
        string? businessKey = null,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(processId))
            throw new ArgumentException("Process ID cannot be empty", nameof(processId));

        if (variables == null)
            throw new ArgumentNullException(nameof(variables));

        _logger?.LogInformation(
            "Starting process '{ProcessId}' with {VariableCount} variables",
            processId,
            variables.Count);

        try
        {
            var request = new StartProcessRequest
            {
                Variables = variables,
                BusinessKey = businessKey
            };

            var processInstance = await _camundaClient.CreateProcessInstanceAsync(
                processId,
                request,
                cancellationToken);

            _logger?.LogInformation(
                "Successfully started process instance {ProcessInstanceKey} for process '{ProcessId}'",
                processInstance.ProcessInstanceKey,
                processId);

            return processInstance;
        }
        catch (Exception ex)
        {
            _logger?.LogError(
                ex,
                "Failed to start process '{ProcessId}'",
                processId);
            throw;
        }
    }
}
