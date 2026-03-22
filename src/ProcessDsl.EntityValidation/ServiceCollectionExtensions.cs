using Microsoft.Extensions.DependencyInjection;
using ProcessDsl.EntityValidation.Models;

namespace ProcessDsl.EntityValidation;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddEntityValidation(
        this IServiceCollection services,
        Action<EntityValidationConfiguration> configureOptions)
    {
        services.Configure(configureOptions);
        services.AddSingleton<IEntitySchemaValidator, EntitySchemaValidator>();
        services.AddHostedService<ProcessEntityValidatorWorker>();
        return services;
    }

    public static IServiceCollection AddEntityValidation(
        this IServiceCollection services,
        string gatewayAddress,
        string contractsBaseDir = "openAPI_contracts")
    {
        return services.AddEntityValidation(options =>
        {
            options.GatewayAddress = gatewayAddress;
            options.ContractsBaseDir = contractsBaseDir;
        });
    }
}
