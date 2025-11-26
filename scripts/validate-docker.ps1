# ============================================================================
# Docker Configuration Validator
# ============================================================================
# This script validates Docker files without needing Docker installed
# ============================================================================

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ValidationResults = @{
    Passed = @()
    Failed = @()
    Warnings = @()
}

# Colors
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "[FAIL] $Message" -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Section { param($Title) Write-Host "`n=== $Title ===" -ForegroundColor Magenta }

Write-Host @"

╔════════════════════════════════════════════════════════════╗
║         Docker Configuration Validator v1.0.0              ║
╚════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# ============================================================================
# 1. Check File Existence
# ============================================================================
Write-Section "File Existence Check"

$RequiredFiles = @{
    "Dockerfile" = "Multi-stage build configuration"
    "docker-compose.yml" = "Production orchestration"
    "docker-compose.dev.yml" = "Development overrides"
    ".dockerignore" = "Build optimization"
    "Makefile" = "Quick commands"
    "scripts\init-db.sql" = "Database initialization"
    ".env.example" = "Environment template"
}

foreach ($file in $RequiredFiles.Keys) {
    if (Test-Path $file) {
        Write-Success "$file exists - $($RequiredFiles[$file])"
        $ValidationResults.Passed += "File: $file"
    } else {
        Write-Failure "$file missing - $($RequiredFiles[$file])"
        $ValidationResults.Failed += "File: $file"
    }
}

# ============================================================================
# 2. Validate Dockerfile
# ============================================================================
Write-Section "Dockerfile Validation"

if (Test-Path "Dockerfile") {
    $dockerfileContent = Get-Content "Dockerfile" -Raw
    
    # Check for multi-stage build
    $stages = [regex]::Matches($dockerfileContent, "FROM .+ as (\w+)")
    if ($stages.Count -ge 5) {
        Write-Success "Multi-stage build detected: $($stages.Count) stages"
        foreach ($stage in $stages) {
            Write-Info "   Stage: $($stage.Groups[1].Value)"
        }
        $ValidationResults.Passed += "Dockerfile: Multi-stage build"
    } else {
        Write-Warning "Expected 5+ stages, found $($stages.Count)"
        $ValidationResults.Warnings += "Dockerfile: Stage count"
    }
    
    # Check for non-root user
    if ($dockerfileContent -match "useradd") {
        Write-Success "Non-root user configured"
        $ValidationResults.Passed += "Dockerfile: Non-root user"
    } else {
        Write-Failure "Non-root user not found"
        $ValidationResults.Failed += "Dockerfile: Non-root user"
    }
    
    # Check for HEALTHCHECK
    if ($dockerfileContent -match "HEALTHCHECK") {
        Write-Success "Health check configured"
        $ValidationResults.Passed += "Dockerfile: HEALTHCHECK"
    } else {
        Write-Warning "No HEALTHCHECK found"
        $ValidationResults.Warnings += "Dockerfile: HEALTHCHECK"
    }
    
    # Check for EXPOSE
    if ($dockerfileContent -match "EXPOSE (\d+)") {
        $port = [regex]::Match($dockerfileContent, "EXPOSE (\d+)").Groups[1].Value
        Write-Success "Port exposed: $port"
        $ValidationResults.Passed += "Dockerfile: EXPOSE $port"
    }
    
    # Check for security best practices
    if ($dockerfileContent -match "apt-get.*rm -rf /var/lib/apt/lists") {
        Write-Success "APT cache cleanup present (security best practice)"
        $ValidationResults.Passed += "Dockerfile: APT cleanup"
    }
    
    if ($dockerfileContent -match "PYTHONUNBUFFERED") {
        Write-Success "Python unbuffered mode enabled"
        $ValidationResults.Passed += "Dockerfile: Python config"
    }
}

# ============================================================================
# 3. Validate docker-compose.yml
# ============================================================================
Write-Section "Docker Compose Validation (Production)"

if (Test-Path "docker-compose.yml") {
    $composeContent = Get-Content "docker-compose.yml" -Raw
    
    # Check version
    if ($composeContent -match "version:\s*['\`"]?([\d.]+)") {
        $version = [regex]::Match($composeContent, "version:\s*['\`"]?([\d.]+)").Groups[1].Value
        Write-Success "Compose version: $version"
        $ValidationResults.Passed += "Compose: Version $version"
    }
    
    # Check services
    $services = @("postgres", "redis", "minio", "backend", "celery-worker", "celery-beat")
    foreach ($service in $services) {
        if ($composeContent -match "^\s+$service\s*:" -or $composeContent -match "^\s{2}$service\s*:") {
            Write-Success "Service defined: $service"
            $ValidationResults.Passed += "Compose: $service service"
        } else {
            Write-Failure "Service missing: $service"
            $ValidationResults.Failed += "Compose: $service service"
        }
    }
    
    # Check health checks
    $healthChecks = [regex]::Matches($composeContent, "healthcheck:")
    if ($healthChecks.Count -gt 0) {
        Write-Success "Health checks configured: $($healthChecks.Count) services"
        $ValidationResults.Passed += "Compose: Health checks"
    } else {
        Write-Warning "No health checks found"
        $ValidationResults.Warnings += "Compose: Health checks"
    }
    
    # Check volumes
    if ($composeContent -match "volumes:\s*$") {
        Write-Success "Named volumes configured"
        $ValidationResults.Passed += "Compose: Volumes"
    }
    
    # Check networks
    if ($composeContent -match "networks:\s*$") {
        Write-Success "Custom network configured"
        $ValidationResults.Passed += "Compose: Networks"
    }
    
    # Check depends_on
    $dependsOn = [regex]::Matches($composeContent, "depends_on:")
    if ($dependsOn.Count -gt 0) {
        Write-Success "Service dependencies configured: $($dependsOn.Count) services"
        $ValidationResults.Passed += "Compose: Dependencies"
    }
}

# ============================================================================
# 4. Validate docker-compose.dev.yml
# ============================================================================
Write-Section "Docker Compose Validation (Development)"

if (Test-Path "docker-compose.dev.yml") {
    $composeDevContent = Get-Content "docker-compose.dev.yml" -Raw
    
    # Check for dev-specific services
    $devServices = @("flower", "pgadmin", "redis-commander")
    $foundDevServices = @()
    foreach ($service in $devServices) {
        if ($composeDevContent -match "^\s+$service\s*:" -or $composeDevContent -match "^\s{2}$service\s*:") {
            Write-Success "Dev service: $service"
            $foundDevServices += $service
        }
    }
    
    if ($foundDevServices.Count -gt 0) {
        Write-Success "Development tools: $($foundDevServices -join ', ')"
        $ValidationResults.Passed += "Compose Dev: Monitoring tools ($($foundDevServices.Count))"
    }
    
    # Check for volume mounts (hot reload)
    if ($composeDevContent -match "./app:/app/app") {
        Write-Success "Hot reload volume mount configured"
        $ValidationResults.Passed += "Compose Dev: Hot reload"
    }
}

# ============================================================================
# 5. Validate .dockerignore
# ============================================================================
Write-Section ".dockerignore Validation"

if (Test-Path ".dockerignore") {
    $dockerignoreContent = Get-Content ".dockerignore"
    
    $criticalPatterns = @{
        "__pycache__" = "Python cache"
        "*.pyc" = "Python bytecode"
        ".env" = "Secrets"
        "venv" = "Virtual environment"
        ".git" = "Git repository"
        "tests" = "Test files"
    }
    
    foreach ($pattern in $criticalPatterns.Keys) {
        if ($dockerignoreContent -match [regex]::Escape($pattern)) {
            Write-Success ".dockerignore excludes: $($criticalPatterns[$pattern]) ($pattern)"
            $ValidationResults.Passed += "Dockerignore: $pattern"
        } else {
            Write-Warning "Missing exclusion: $($criticalPatterns[$pattern]) ($pattern)"
            $ValidationResults.Warnings += "Dockerignore: $pattern"
        }
    }
    
    $lineCount = $dockerignoreContent.Count
    Write-Info "Total exclusion patterns: $lineCount"
}

# ============================================================================
# 6. Validate Environment Template
# ============================================================================
Write-Section "Environment Configuration"

if (Test-Path ".env.example") {
    $envContent = Get-Content ".env.example" -Raw
    
    $requiredVars = @{
        "SECRET_KEY" = "Application secret"
        "JWT_SECRET" = "JWT signing key"
        "POSTGRES_PASSWORD" = "Database password"
        "REDIS_PASSWORD" = "Redis password"
        "GEMINI_API_KEY" = "Gemini AI key"
        "PYANNOTE_AUTH_TOKEN" = "Pyannote HuggingFace token"
    }
    
    foreach ($var in $requiredVars.Keys) {
        if ($envContent -match $var) {
            Write-Success "Env var defined: $var - $($requiredVars[$var])"
            $ValidationResults.Passed += "Env: $var"
        } else {
            Write-Failure "Missing env var: $var - $($requiredVars[$var])"
            $ValidationResults.Failed += "Env: $var"
        }
    }
    
    # Check for actual .env file
    if (Test-Path ".env") {
        Write-Info ".env file exists (production ready)"
    } else {
        Write-Warning ".env file not found (create from .env.example)"
        $ValidationResults.Warnings += "Env: .env file missing"
    }
}

# ============================================================================
# 7. Validate Makefile
# ============================================================================
Write-Section "Makefile Validation"

if (Test-Path "Makefile") {
    $makefileContent = Get-Content "Makefile" -Raw
    
    $essentialTargets = @("help", "build", "up", "down", "dev-build", "dev-up", "test", "clean")
    foreach ($target in $essentialTargets) {
        if ($makefileContent -match "^$target\s*:") {
            Write-Success "Makefile target: $target"
            $ValidationResults.Passed += "Makefile: $target"
        }
    }
    
    # Count total targets
    $totalTargets = [regex]::Matches($makefileContent, "^[\w-]+\s*:.*##", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    Write-Info "Total documented commands: $($totalTargets.Count)"
}

# ============================================================================
# 8. Validate Database Init Script
# ============================================================================
Write-Section "Database Initialization"

if (Test-Path "scripts\init-db.sql") {
    $initSqlContent = Get-Content "scripts\init-db.sql" -Raw
    
    if ($initSqlContent -match "CREATE EXTENSION") {
        Write-Success "PostgreSQL extensions configured"
        $ValidationResults.Passed += "DB Init: Extensions"
    }
    
    if ($initSqlContent -match "CREATE TYPE.*ENUM") {
        Write-Success "Custom types defined"
        $ValidationResults.Passed += "DB Init: Custom types"
    }
    
    if ($initSqlContent -match "GRANT") {
        Write-Success "Permissions granted"
        $ValidationResults.Passed += "DB Init: Permissions"
    }
}

# ============================================================================
# 9. Security Audit
# ============================================================================
Write-Section "Security Audit"

# Check for hardcoded secrets in docker files
$securityIssues = @()

$dockerFiles = @("Dockerfile", "docker-compose.yml", "docker-compose.dev.yml")
foreach ($file in $dockerFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        
        # Check for hardcoded passwords (except dev examples)
        if ($content -match "password\s*[:=]\s*['\`"](?!.*\{|\$)" -and $file -notmatch "dev") {
            $securityIssues += "$file may contain hardcoded password"
        }
        
        # Check for hardcoded API keys
        if ($content -match "api[_-]?key\s*[:=]\s*['\`"][^{$]" -and $file -notmatch "dev") {
            $securityIssues += "$file may contain hardcoded API key"
        }
    }
}

if ($securityIssues.Count -eq 0) {
    Write-Success "No hardcoded secrets detected"
    $ValidationResults.Passed += "Security: No hardcoded secrets"
} else {
    foreach ($issue in $securityIssues) {
        Write-Warning $issue
        $ValidationResults.Warnings += "Security: $issue"
    }
}

# ============================================================================
# 10. Best Practices Check
# ============================================================================
Write-Section "Best Practices"

if (Test-Path "Dockerfile") {
    $dockerfileContent = Get-Content "Dockerfile" -Raw
    
    # Check layer optimization
    if ($dockerfileContent -match "COPY requirements.txt.*\nRUN.*pip install") {
        Write-Success "Dependency layer cached separately (optimization)"
        $ValidationResults.Passed += "Best Practice: Layer caching"
    }
    
    # Check for .dockerignore usage
    if (Test-Path ".dockerignore") {
        Write-Success ".dockerignore reduces build context"
        $ValidationResults.Passed += "Best Practice: .dockerignore"
    }
    
    # Check for multi-stage reduction
    if ($dockerfileContent -match "FROM.*as builder" -and $dockerfileContent -match "COPY --from=builder") {
        Write-Success "Multi-stage build reduces image size"
        $ValidationResults.Passed += "Best Practice: Multi-stage"
    }
}

# ============================================================================
# Summary
# ============================================================================
Write-Section "Validation Summary"

Write-Host ""
Write-Host "[RESULTS] Validation Summary:" -ForegroundColor White
Write-Host "   [OK] Passed:   $($ValidationResults.Passed.Count)" -ForegroundColor Green
Write-Host "   [WARN] Warnings: $($ValidationResults.Warnings.Count)" -ForegroundColor Yellow
Write-Host "   [FAIL] Failed:   $($ValidationResults.Failed.Count)" -ForegroundColor Red

if ($ValidationResults.Failed.Count -eq 0) {
    Write-Host "`n[SUCCESS] All critical validations passed!" -ForegroundColor Green
    Write-Host "          Your Docker configuration is ready for deployment!" -ForegroundColor Green
    $exitCode = 0
} else {
    Write-Host "`n[ERROR] Some validations failed. Please review:" -ForegroundColor Yellow
    foreach ($failure in $ValidationResults.Failed) {
        Write-Host "   - $failure" -ForegroundColor Red
    }
    $exitCode = 1
}

if ($ValidationResults.Warnings.Count -gt 0) {
    Write-Host "`n[WARN] Warnings (non-critical):" -ForegroundColor Yellow
    foreach ($warning in $ValidationResults.Warnings) {
        Write-Host "   - $warning" -ForegroundColor DarkYellow
    }
}

Write-Host "`n[NEXT] Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Ensure Docker Desktop is running" -ForegroundColor White
Write-Host "   2. Create .env from .env.example: cp .env.example .env" -ForegroundColor White
Write-Host "   3. Fill required secrets in .env" -ForegroundColor White
Write-Host "   4. Build images: make dev-build" -ForegroundColor White
Write-Host "   5. Start services: make dev-up" -ForegroundColor White
Write-Host "   6. Check health: make health" -ForegroundColor White
Write-Host ""

exit $exitCode
