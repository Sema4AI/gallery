## Gallery publisher

Scripts here build the Action and Agent packages + the manifest.json files needed to publish these to clients (Studio and Control Room).

## Development

1. Open project via: [publisher.code-workspace](publisher.code-workspace) to get both the publisher and GHA flows in VS Code/Cursor at the same time
2. Have RCC setup to enable simple local testing: `rcc run -t "<task>"` (see [robot.yaml](robot.yaml) for the options).

Nothing goes to S3 from local machines so the scripts can be executed locally without worry.
Only GitHub actions update the S3.
