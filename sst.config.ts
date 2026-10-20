/// <reference path="./.sst/platform/config.d.ts" />
export default $config({
  app(input) {
    return {
      name: "our-wedding",
      home: "aws",
      removal: input?.stage?.startsWith("production") ? "retain" : "remove",
      protect: input?.stage?.startsWith("production"),
      providers: { aws: { region: "eu-central-1" } },
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
    // Separate state prevents a DNS bootstrap rerun from removing the application.
    if ($app.stage === "production-dns") {
      const zone = new aws.route53.Zone("DomainZone", { name: domain });
      const identity = new aws.ses.DomainIdentity("EmailIdentity", { domain });
      new aws.route53.Record("EmailVerification", {
        zoneId: zone.zoneId,
        name: `_amazonses.${domain}`,
        type: "TXT",
        ttl: 300,
        records: [$interpolate`"${identity.verificationToken}"`],
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
        records: ['"v=DMARC1; p=none;"'],
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
    const zone = aws.route53.getZoneOutput({
      name: domain,
      privateZone: false,
    });
    const docker = await import("@pulumi/docker-build");
    const emailFrom = process.env.EMAIL_FROM;
    const identityArn =
      process.env.SES_IDENTITY_ARN ||
      $interpolate`arn:aws:ses:eu-central-1:${aws.getCallerIdentityOutput().accountId}:identity/${domain}`;
    if (
      !emailFrom ||
      (!!process.env.SES_IDENTITY_ARN &&
        !/^arn:aws:ses:eu-central-1:\d{12}:identity\/.+$/.test(
          process.env.SES_IDENTITY_ARN,
        ))
    ) {
      throw new Error(
        "Set EMAIL_FROM for the managed domain, or supply a valid SES_IDENTITY_ARN in eu-central-1.",
      );
    }
    const encryptionKey = new sst.Secret("InviteEncryptionKey");
    const database = new sst.aws.Dsql("Database", {
      transform: {
        cluster: { deletionProtectionEnabled: $app.stage === "production" },
      },
    });
    const photos = new sst.aws.Bucket("Photos", {
      cors: false,
      transform: {
        lifecycle: (args) => {
          args.rules = $output(args.rules).apply((rules) =>
            (rules ?? []).map((rule) => ({
              ...rule,
              abortIncompleteMultipartUpload: { daysAfterInitiation: 1 },
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
      router: { instance: router },
      build: { command: "npm run build", output: "build" },
      environment: { PUBLIC_API_URL: "/api" },
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
            action: { type: "expire" },
          },
        ],
      }),
    });
    const registryAuth = aws.ecr.getAuthorizationTokenOutput({
      registryId: repository.registryId,
    });
    const image = new docker.Image("ApiContainer", {
      context: { location: "." },
      dockerfile: { location: "backend/Dockerfile" },
      target: "lambda",
      platforms: ["linux/amd64"],
      push: true,
      exec: true,
      buildOnPreview: false,
      exports: [{ registry: { ociMediaTypes: false } }],
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
            Principal: { Service: "lambda.amazonaws.com" },
            Action: "sts:AssumeRole",
          },
        ],
      }),
    });
    const logs = new aws.cloudwatch.LogGroup("ApiLogs", { retentionInDays: 7 });
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
            Action: ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"],
            Resource: [
              $interpolate`${photos.arn}/originals/*`,
              $interpolate`${photos.arn}/previews/*`,
            ],
          },
          {
            Effect: "Allow",
            Action: ["ses:SendEmail", "ses:SendRawEmail"],
            Resource: identityArn,
            Condition: { StringEquals: { "ses:FromAddress": emailFrom } },
          },
        ],
      }),
    });
    const fn = new aws.lambda.Function(
      "FastApi",
      {
        packageType: "Image",
        imageUri: image.ref,
        role: role.arn,
        architectures: ["x86_64"],
        memorySize: 1024,
        timeout: 29,
        reservedConcurrentExecutions: 5,
        loggingConfig: { logFormat: "Text", logGroup: logs.name },
        environment: {
          variables: {
            DSQL_HOST: database.endpoint,
            DB_USER: "wedding_app",
            BUCKET_NAME: photos.name,
            INVITE_ENCRYPTION_KEY: encryptionKey.value,
            SITE_URL: router.url,
            COOKIE_SECURE: "true",
            EMAIL_FROM: emailFrom,
            RSVP_NOTIFICATION_EMAIL: process.env.RSVP_NOTIFICATION_EMAIL ?? "",
          },
        },
      },
      { dependsOn: [permissions] },
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
      website: site.url,
      databaseHost: database.endpoint,
      runtimeRoleArn: role.arn,
      databaseArn: database.nodes.cluster.arn,
      photos: photos.name,
    };
  },
});
