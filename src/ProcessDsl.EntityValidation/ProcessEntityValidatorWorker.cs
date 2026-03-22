using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using ProcessDsl.EntityValidation.Models;
using Zeebe.Client;
using Zeebe.Client.Api.Responses;
using Zeebe.Client.Api.Worker;

namespace ProcessDsl.EntityValidation;

public class ProcessEntityValidatorWorker : IHostedService, IDisposable
{
    private const string TaskType = "process-entity-validator";

    private readonly IZeebeClient _zeebeClient;
    private readonly IEntitySchemaValidator _validator;
    private readonly ILogger<ProcessEntityValidatorWorker> _logger;
    private IJobWorker? _worker;

    public ProcessEntityValidatorWorker(
        IOptions<EntityValidationConfiguration> config,
        IEntitySchemaValidator validator,
        ILogger<ProcessEntityValidatorWorker> logger)
    {
        _validator = validator;
        _logger = logger;

        var cfg = config.Value;
        if (cfg.UsePlainText)
        {
            _zeebeClient = ZeebeClient.Builder()
                .UseGatewayAddress(cfg.GatewayAddress)
                .UsePlainText()
                .Build();
        }
        else
        {
            if (string.IsNullOrEmpty(cfg.AuthToken))
                throw new InvalidOperationException("AuthToken is required when UsePlainText is false");

            _zeebeClient = ZeebeClient.Builder()
                .UseGatewayAddress(cfg.GatewayAddress)
                .UseTransportEncryption()
                .UseAccessToken(cfg.AuthToken)
                .Build();
        }
    }

    public Task StartAsync(CancellationToken cancellationToken)
    {
        _worker = _zeebeClient.NewWorker()
            .JobType(TaskType)
            .Handler(HandleJobAsync)
            .Name("entity-validator-worker")
            .Open();

        _logger.LogInformation("Process Entity Validator worker started (task type: {TaskType})", TaskType);
        return Task.CompletedTask;
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _worker?.Dispose();
        _zeebeClient.Dispose();
        _logger.LogInformation("Process Entity Validator worker stopped");
        await Task.CompletedTask;
    }

    private async Task HandleJobAsync(IJobClient jobClient, IJob job)
    {
        _logger.LogDebug("Processing job {JobKey}", job.Key);

        var variables = string.IsNullOrEmpty(job.Variables)
            ? new JObject()
            : JObject.Parse(job.Variables);

        var headers = string.IsNullOrEmpty(job.CustomHeaders)
            ? new JObject()
            : JObject.Parse(job.CustomHeaders);

        var processEntity = variables["processEntity"];
        var entityName = headers["entityName"]?.ToString();
        var entityModel = headers["entityModel"]?.ToString();

        var result = _validator.Validate(processEntity, entityName, entityModel);

        var payload = JsonConvert.SerializeObject(new { validationResult = result });

        await jobClient.NewCompleteJobCommand(job.Key)
            .Variables(payload)
            .Send();
    }

    public void Dispose()
    {
        _worker?.Dispose();
        _zeebeClient.Dispose();
    }
}
