using ProcessDsl.EntityValidation;

var builder = Host.CreateDefaultBuilder(args);

builder.ConfigureServices((context, services) =>
{
    services.AddEntityValidation(options =>
    {
        options.GatewayAddress = context.Configuration["Zeebe:GatewayAddress"] ?? "localhost:26500";
        options.ContractsBaseDir = context.Configuration["Validation:ContractsBaseDir"] ?? "openAPI_contracts";
        options.UsePlainText = bool.Parse(context.Configuration["Zeebe:UsePlainText"] ?? "true");
        options.AuthToken = context.Configuration["Zeebe:AuthToken"];
    });
});

var host = builder.Build();
await host.RunAsync();
