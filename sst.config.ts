/// <reference path="./.sst/platform/config.d.ts" />
export default $config({
  app(input) {
    return {
      name: "our-wedding",
      home: "aws",
      removal: input?.stage?.startsWith("production") ? "retain" : "remove",
      protect: input?.stage?.startsWith("production"),
      providers: {
        aws: { region: "eu-central-1" },
      },
    };
  },
  async run() {
    const domain = process.env.SITE_DOMAIN?.toLowerCase();
    if (
      !domain ||
      domain.length > 253 ||
      !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain)
    ) {
      throw new Error(
        "Set SITE_DOMAIN to a domain name without a scheme, path or whitespace.",
      );
    }
    const zoneIds = await aws.route53.getZones();
    const zones = await Promise.all(
      zoneIds.ids.map((zoneId) => aws.route53.getZone({ zoneId })),
    );
    const matches = zones.filter(
      (zone) =>
        !zone.privateZone &&
        zone.name.replace(/\.$/, "").toLowerCase() === domain,
    );
    if (matches.length > 1) {
      throw new Error(
        "Multiple public hosted zones match SITE_DOMAIN. Reconcile the duplicate zones before deploying.",
      );
    }
    const existingZone = matches[0];
    if ($app.stage === "production-dns") {
      // Keep the resource declared on every run: import an existing zone or create
      // one if absent. Switching a managed zone to a lookup would remove it from state.
      const zone = new aws.route53.Zone(
        "DomainZone",
        { name: domain },
        {
          import: existingZone?.zoneId,
          protect: true,
          retainOnDelete: true,
        },
      );
      const resendDkim = new sst.Secret("ResendDkim");
      const resendRsend = new sst.Secret("ResendRsend");
      const resendSend = new sst.Secret("ResendSend");
      const resendReceivingMx = new sst.Secret("ResendReceivingMx");
      new aws.route53.Record("ResendReceivingMxRecord", {
        zoneId: zone.zoneId,
        name: domain,
        type: "MX",
        ttl: 300,
        records: [
          resendReceivingMx.value.apply((value) => {
            const match =
              /^(\d{1,5}) ((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\.?)$/i.exec(
                value,
              );
            if (
              !match ||
              Number(match[1]) > 65535 ||
              match[2].length > 254 ||
              value.trim() !== value
            ) {
              throw new Error(
                "ResendReceivingMx must contain an MX priority and DNS hostname, separated by one space.",
              );
            }
            return value;
          }),
        ],
      });
      new aws.route53.Record("ResendDkimRecord", {
        zoneId: zone.zoneId,
        name: `resend._domainkey.${domain}`,
        type: "TXT",
        ttl: 300,
        records: [
          resendDkim.value.apply((value) => {
            // Supply the raw Resend value; the provider adds the outer TXT quotes.
            // DNS limits each string to 255 bytes, so split long ASCII DKIM keys.
            if (!value.trim() || /[^\x20-\x7e]|["\\]/.test(value)) {
              throw new Error(
                "ResendDkim must contain the unquoted, single-line DKIM value.",
              );
            }
            return value.match(/.{1,255}/g)!.join('""');
          }),
        ],
      });
      for (const [name, secret] of [
        ["rsend", resendRsend],
        ["send", resendSend],
      ] as const) {
        new aws.route53.Record(
          name === "rsend" ? "ResendRsendRecord" : "ResendSendRecord",
          {
            zoneId: zone.zoneId,
            name: `${name}.${domain}`,
            type: "CNAME",
            ttl: 300,
            records: [
              secret.value.apply((value) => {
                if (
                  !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\.?$/i.test(
                    value,
                  ) ||
                  value.length > 254
                ) {
                  throw new Error(
                    "Resend CNAME secrets must contain a DNS hostname only.",
                  );
                }
                return value;
              }),
            ],
          },
        );
      }
      // Legacy SES DNS resources stay managed to avoid destructive changes to the
      // existing protected DNS stage. Production delivery uses Resend exclusively.
      const identity = new aws.ses.DomainIdentity("EmailIdentity", {
        domain,
      });
      // The AWS provider adds Route 53's TXT quotes; pass unquoted values here.
      new aws.route53.Record("EmailVerification", {
        zoneId: zone.zoneId,
        name: `_amazonses.${domain}`,
        type: "TXT",
        ttl: 300,
        records: [identity.verificationToken],
      });
      const dkim = new aws.ses.DomainDkim("EmailDkim", {
        domain: identity.domain,
      });
      for (let i = 0; i < 3; i++) {
        new aws.route53.Record(`EmailDkim${i}`, {
          zoneId: zone.zoneId,
          name: $interpolate`${dkim.dkimTokens[i]}._domainkey.${domain}`,
          type: "CNAME",
          ttl: 300,
          records: [$interpolate`${dkim.dkimTokens[i]}.dkim.amazonses.com`],
        });
      }
      new aws.route53.Record("EmailDmarc", {
        zoneId: zone.zoneId,
        name: `_dmarc.${domain}`,
        type: "TXT",
        ttl: 300,
        records: ["v=DMARC1; p=none"],
      });
      return {
        domain,
        hostedZoneId: zone.zoneId,
        nameservers: zone.nameServers,
        emailIdentityArn: identity.arn,
      };
    }
    if ($app.stage !== "production") {
      throw new Error(
        "Use production-dns for DNS setup or production for the website.",
      );
    }
    if (!existingZone) {
      throw new Error("No public hosted zone matches SITE_DOMAIN. Run setup-dns first.");
    }
    const zone = existingZone;
    const docker = await import("@pulumi/docker-build");
    const path = await import("node:path");
    const emailFrom = process.env.EMAIL_FROM;
    if (!emailFrom || !/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(emailFrom)) {
      throw new Error("Set EMAIL_FROM to an address on a Resend-verified domain.");
    }
    const resendApiKey = new sst.Secret("ResendApiKey");
    const encryptionKey = new sst.Secret("InviteEncryptionKey");
    const adminPassword = new sst.Secret("AdminPassword");
    const adminUsername = process.env.ADMIN_USERNAME;
    if (!adminUsername || !/^[a-zA-Z0-9_.@+-]{3,100}$/.test(adminUsername)) {
      throw new Error("Set ADMIN_USERNAME to 3–100 letters, digits, or _.@+-.");
    }
    const hostKeys = [
      "WEDDING_GROOM_NAME",
      "WEDDING_GROOM_EMAIL",
      "WEDDING_BRIDE_NAME",
      "WEDDING_BRIDE_EMAIL",
    ];
    for (const key of hostKeys) {
      if (!process.env[key]?.trim())
        throw new Error(`Set ${key} before deployment.`);
    }
    const database = new sst.aws.Dsql("Database", {
      transform: {
        cluster: {
          deletionProtectionEnabled: $app.stage === "production",
        },
      },
    });
    // Public editorial images are intentionally separate from private guest uploads.
    const landingImages = new sst.aws.Bucket("LandingImages", { access: "public" });
    const photos = new sst.aws.Bucket("Photos", {
      cors: false,
      transform: {
        lifecycle: (args) => {
          args.rules = $output(args.rules).apply((rules) =>
            (rules ?? []).map((rule) => ({
              ...rule,
              abortIncompleteMultipartUpload: {
                daysAfterInitiation: 1,
              },
            })),
          );
        },
      },
      lifecycle: [
        {
          id: "expire-unfinished-uploads",
          prefix: "pending/",
          expiresIn: "1 day",
        },
      ],
    });
    const router = new sst.aws.Router("Router", {
      domain: {
        name: domain,
        redirects: [`www.${domain}`],
        dns: sst.aws.dns({ zone: zone.zoneId }),
      },
      edge: {
        viewerResponse: {
          injection: `
            event.response.headers['x-content-type-options'] = { value: 'nosniff' };
            event.response.headers['x-frame-options'] = { value: 'DENY' };
            event.response.headers['strict-transport-security'] = { value: 'max-age=31536000' };
            event.response.headers['referrer-policy'] = { value: event.request.uri.startsWith('/api/admin') ? 'same-origin' : 'no-referrer' };
          `,
        },
      },
    });
    const site = new sst.aws.StaticSite("Wedding", {
      path: "frontend",
      router: {
        instance: router,
      },
      build: {
        command: "npm run build",
        output: "build",
      },
      environment: {
        PUBLIC_API_URL: "/api",
        PUBLIC_CONTACT_EMAIL: emailFrom,
        PUBLIC_ASSET_URL: $interpolate`https://${landingImages.domain}`,
      },
    });
    new aws.s3.BucketCorsConfiguration("PhotoCors", {
      bucket: photos.name,
      corsRules: [
        {
          allowedOrigins: [router.url],
          allowedMethods: ["GET", "POST", "PUT"],
          allowedHeaders: ["*"],
          exposeHeaders: ["ETag"],
          maxAgeSeconds: 3600,
        },
      ],
    });
    const repository = new aws.ecr.Repository("ApiImage", {
      // ECR rejects uppercase characters in Pulumi's generated physical name.
      name: `${$app.name}-${$app.stage}-api`.toLowerCase(),
      forceDelete: $app.stage !== "production",
    });
    new aws.ecr.LifecyclePolicy("ApiImageRetention", {
      repository: repository.name,
      policy: JSON.stringify({
        rules: [
          {
            rulePriority: 1,
            selection: {
              tagStatus: "any",
              countType: "imageCountMoreThan",
              countNumber: 10,
            },
            action: {
              type: "expire",
            },
          },
        ],
      }),
    });
    const registryAuth = aws.ecr.getAuthorizationTokenOutput({
      registryId: repository.registryId,
    });
    const image = new docker.Image("ApiContainer", {
      // The Docker provider runs from .sst/platform, not the project root.
      context: {
        location: $cli.paths.root,
      },
      dockerfile: {
        location: path.join($cli.paths.root, "backend", "Dockerfile"),
      },
      target: "lambda",
      platforms: ["linux/amd64"],
      // Push the image to ECR using Buildx.
      push: true,
      exec: false,
      buildOnPreview: false,
      tags: [
        $interpolate`${repository.repositoryUrl}:${process.env.GITHUB_SHA ?? "local"}`,
      ],
      registries: [
        {
          address: repository.repositoryUrl,
          username: registryAuth.userName,
          password: registryAuth.password,
        },
      ],
    });
    const role = new aws.iam.Role("ApiRole", {
      assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Principal: {
              Service: "lambda.amazonaws.com",
            },
            Action: "sts:AssumeRole",
          },
        ],
      }),
    });
    const logs = new aws.cloudwatch.LogGroup("ApiLogs", {
      retentionInDays: 7,
    });
    const permissions = new aws.iam.RolePolicy("ApiPermissions", {
      role: role.id,
      policy: $jsonStringify({
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Action: ["logs:CreateLogStream", "logs:PutLogEvents"],
            Resource: $interpolate`${logs.arn}:*`,
          },
          {
            Effect: "Allow",
            Action: ["dsql:DbConnect"],
            Resource: database.nodes.cluster.arn,
          },
          {
            Effect: "Allow",
            Action: [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject",
              "s3:AbortMultipartUpload",
            ],
            Resource: $interpolate`${photos.arn}/pending/*`,
          },
          {
            Effect: "Allow",
            Action: [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject",
              "s3:AbortMultipartUpload",
            ],
            Resource: [
              $interpolate`${photos.arn}/originals/*`,
              $interpolate`${photos.arn}/previews/*`,
            ],
          },
        ],
      }),
    });
    const imageUri = image.ref.apply((ref) => {
      const separator = ref.indexOf("@sha256:");
      if (separator === -1) return ref;
      return `${ref.slice(0, separator).replace(/:[^/:]+$/, "")}${ref.slice(separator)}`;
    });
    const bootstrapRole = new aws.iam.Role("BootstrapRole", {
      assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Principal: { Service: "lambda.amazonaws.com" },
            Action: "sts:AssumeRole",
          },
        ],
      }),
    });
    const bootstrapLogs = new aws.cloudwatch.LogGroup("BootstrapLogs", {
      retentionInDays: 7,
    });
    const bootstrapPermissions = new aws.iam.RolePolicy(
      "BootstrapPermissions",
      {
        role: bootstrapRole.id,
        policy: $jsonStringify({
          Version: "2012-10-17",
          Statement: [
            {
              Effect: "Allow",
              Action: ["logs:CreateLogStream", "logs:PutLogEvents"],
              Resource: $interpolate`${bootstrapLogs.arn}:*`,
            },
            {
              Effect: "Allow",
              Action: "dsql:DbConnectAdmin",
              Resource: database.nodes.cluster.arn,
            },
          ],
        }),
      },
    );
    const bootstrap = new aws.lambda.Function(
      "Bootstrap",
      {
        packageType: "Image",
        imageUri,
        imageConfig: {
          commands: [
            "uvicorn",
            "app.bootstrap:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--no-access-log",
          ],
        },
        role: bootstrapRole.arn,
        architectures: ["x86_64"],
        memorySize: 1024,
        timeout: 900,
        loggingConfig: { logFormat: "Text", logGroup: bootstrapLogs.name },
        environment: {
          variables: {
            DSQL_HOST: database.endpoint,
            DB_USER: "admin",
            INVITE_ENCRYPTION_KEY: "unused-for-bootstrap",
            ADMIN_USERNAME: adminUsername,
            ADMIN_PASSWORD: adminPassword.value,
            RUNTIME_ROLE_ARN: role.arn,
            DEBUG_DEPLOY: process.env.DEBUG_DEPLOY === "1" ? "1" : "0",
            SITE_URL: router.url,
            ...Object.fromEntries(
              hostKeys.map((key) => [key, process.env[key]!]),
            ),
          },
        },
      },
      { dependsOn: [bootstrapPermissions] },
    );
    const initialization = new aws.lambda.Invocation(
      "InitializeApplication",
      {
        functionName: bootstrap.name,
        // Retry idempotent initialization on each deploy, including after partial failures.
        triggers: { deployment: Date.now().toString() },
        input: JSON.stringify({
          version: "2.0",
          routeKey: "POST /bootstrap",
          rawPath: "/bootstrap",
          rawQueryString: "",
          headers: { host: "bootstrap.internal", "x-forwarded-proto": "https" },
          requestContext: {
            apiId: "bootstrap",
            domainName: "bootstrap.internal",
            domainPrefix: "bootstrap",
            requestId: "sst-bootstrap",
            routeKey: "POST /bootstrap",
            stage: "$default",
            time: "01/Jan/2026:00:00:00 +0000",
            timeEpoch: 1767225600000,
            http: {
              method: "POST",
              path: "/bootstrap",
              protocol: "HTTP/1.1",
              sourceIp: "127.0.0.1",
              userAgent: "sst-bootstrap",
            },
          },
          isBase64Encoded: false,
        }),
      },
      {
        dependsOn: [bootstrap, site],
        customTimeouts: { create: "20m", update: "20m" },
      },
    );
    const bootstrapStatus = initialization.result.apply((result) => {
      const response = JSON.parse(result);
      const body = JSON.parse(response.body ?? "{}");
      if (response.statusCode !== 200 || body.ok !== true) {
        throw new Error(
          process.env.DEBUG_DEPLOY === "1"
            ? `Deployment initialization failed during ${body.phase ?? "unknown phase"}: ${body.error ?? response.body ?? result}`
            : "Deployment initialization failed; inspect the private bootstrap configuration and database migration state.",
        );
      }
      return { admin: body.admin as string };
    });
    const fn = new aws.lambda.Function(
      "FastApi",
      {
        packageType: "Image",
        // Pulumi may return repository:tag@sha256:digest; Lambda expects
        // repository@sha256:digest (or repository:tag).
        imageUri: bootstrapStatus.apply(() => imageUri),
        role: role.arn,
        architectures: ["x86_64"],
        memorySize: 1024,
        timeout: 29,
        loggingConfig: {
          logFormat: "Text",
          logGroup: logs.name,
        },
        environment: {
          variables: {
            DSQL_HOST: database.endpoint,
            DB_USER: "wedding_app",
            BUCKET_NAME: photos.name,
            INVITE_ENCRYPTION_KEY: encryptionKey.value,
            SITE_URL: router.url,
            COOKIE_SECURE: "true",
            EMAIL_FROM: emailFrom,
            EMAIL_PROVIDER: "resend",
            RESEND_API_KEY: resendApiKey.value,
            RSVP_NOTIFICATION_EMAIL: process.env.RSVP_NOTIFICATION_EMAIL ?? "",
          },
        },
      },
      {
        dependsOn: [permissions],
      },
    );
    const warmupGroup = new aws.scheduler.ScheduleGroup("ApiWarmupGroup");
    const warmupRole = new aws.iam.Role("ApiWarmupRole", {
      assumeRolePolicy: $jsonStringify({
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Principal: { Service: "scheduler.amazonaws.com" },
            Action: "sts:AssumeRole",
            Condition: {
              StringEquals: {
                "aws:SourceAccount": aws.getCallerIdentityOutput().accountId,
              },
              ArnEquals: { "aws:SourceArn": warmupGroup.arn },
            },
          },
        ],
      }),
    });
    const warmupPermission = new aws.iam.RolePolicy("ApiWarmupPermission", {
      role: warmupRole.id,
      policy: $jsonStringify({
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Action: "lambda:InvokeFunction",
            Resource: fn.arn,
          },
        ],
      }),
    });
    new aws.scheduler.Schedule(
      "ApiWeddingWarmup",
      {
        groupName: warmupGroup.name,
        description:
          "Warm the admin/gallery API and database during the wedding period",
        scheduleExpression: "cron(0/5 10-11 ? * * *)",
        scheduleExpressionTimezone: "Europe/Rome",
        flexibleTimeWindow: { mode: "OFF" },
        target: {
          arn: fn.arn,
          roleArn: warmupRole.arn,
          // Lambda Web Adapter requires an HTTP event, not a bare scheduled event.
          input: JSON.stringify({
            version: "2.0",
            routeKey: "GET /api/health",
            rawPath: "/api/health",
            rawQueryString: "",
            headers: { host: domain, "x-forwarded-proto": "https" },
            requestContext: {
              apiId: "scheduled-warmup",
              domainName: domain,
              domainPrefix: "scheduled-warmup",
              http: {
                method: "GET",
                path: "/api/health",
                protocol: "HTTP/1.1",
                sourceIp: "127.0.0.1",
                userAgent: "wedding-scheduled-warmup",
              },
              requestId: "<aws.scheduler.execution-id>",
              routeKey: "GET /api/health",
              stage: "$default",
              time: "<aws.scheduler.scheduled-time>",
              timeEpoch: 0,
            },
            isBase64Encoded: false,
          }),
          retryPolicy: {
            maximumRetryAttempts: 0,
            maximumEventAgeInSeconds: 60,
          },
        },
      },
      { dependsOn: [warmupPermission] },
    );
    const api = new sst.aws.ApiGatewayV2("Api", {
      cors: false,
      transform: {
        stage: {
          defaultRouteSettings: {
            throttlingBurstLimit: 20,
            throttlingRateLimit: 10,
          },
        },
      },
    });
    api.route("$default", fn.arn);
    router.route("/api", api.url);
    return {
      bootstrapStatus,
      website: site.url,
      databaseHost: database.endpoint,
      runtimeRoleArn: role.arn,
      databaseArn: database.nodes.cluster.arn,
      photos: photos.name,
      landingImages: landingImages.name,
      landingImagesUrl: $interpolate`https://${landingImages.domain}`,
    };
  },
});
