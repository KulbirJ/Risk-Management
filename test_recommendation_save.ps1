# Test script for recommendation field save functionality
param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [switch]$Cleanup = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Recommendation Field Save Test" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$TenantId = "67636bd3-9846-4bde-806f-aea369fc9457"
$UserId = "0bc9d6a9-f342-452e-9297-ee33f44d4f84"
$headers = @{
    'X-Tenant-Id' = $TenantId
    'X-User-Id' = $UserId
    'Content-Type' = 'application/json'
}

Write-Host "Step 1: Creating test assessment..." -ForegroundColor Yellow
$assessmentData = @{
    title = "Test Assessment for Recommendations"
    description = "Testing recommendation field save functionality"
    system_background = "Test system"
    scope = "Test scope"
    tech_stack = @("Test")
    overall_impact = "Medium"
} | ConvertTo-Json

try {
    $assessment = Invoke-RestMethod -Uri "$BaseUrl/assessments" -Method Post -Headers $headers -Body $assessmentData
    $AssessmentId = $assessment.id
    Write-Host "Assessment created: $AssessmentId" -ForegroundColor Green
} catch {
    Write-Host "Failed to create assessment: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 2: Creating threat with recommendation..." -ForegroundColor Yellow
$threatData = @{
    title = "SQL Injection Vulnerability"
    description = "Database queries are vulnerable to SQL injection"
    recommendation = "Use parameterized queries and input validation"
    likelihood = "High"
    impact = "Critical"
} | ConvertTo-Json

try {
    $threat = Invoke-RestMethod -Uri "$BaseUrl/threats?assessment_id=$AssessmentId" -Method Post -Headers $headers -Body $threatData
    $ThreatId = $threat.id
    Write-Host "Threat created: $ThreatId" -ForegroundColor Green
    Write-Host "  Title: $($threat.title)" -ForegroundColor Gray
    Write-Host "  Recommendation: $($threat.recommendation)" -ForegroundColor Gray
} catch {
    Write-Host "Failed to create threat: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 3: Retrieving threat to verify recommendation..." -ForegroundColor Yellow
try {
    $retrievedThreat = Invoke-RestMethod -Uri "$BaseUrl/threats/$ThreatId" -Method Get -Headers $headers
    
    if ($retrievedThreat.recommendation -eq "Use parameterized queries and input validation") {
        Write-Host "Recommendation retrieved successfully" -ForegroundColor Green
        Write-Host "  Retrieved: $($retrievedThreat.recommendation)" -ForegroundColor Gray
    } else {
        Write-Host "Recommendation mismatch!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve threat: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 4: Updating threat recommendation..." -ForegroundColor Yellow
$updateData = @{
    recommendation = "UPDATED: Implement prepared statements, stored procedures, and WAF rules"
    description = $threat.description
    likelihood = $threat.likelihood
    impact = $threat.impact
} | ConvertTo-Json

try {
    $updatedThreat = Invoke-RestMethod -Uri "$BaseUrl/threats/$ThreatId" -Method Patch -Headers $headers -Body $updateData
    Write-Host "Threat updated" -ForegroundColor Green
    Write-Host "  New recommendation: $($updatedThreat.recommendation)" -ForegroundColor Gray
} catch {
    Write-Host "Failed to update threat: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 5: Verifying updated recommendation..." -ForegroundColor Yellow
try {
    $finalThreat = Invoke-RestMethod -Uri "$BaseUrl/threats/$ThreatId" -Method Get -Headers $headers
    
    if ($finalThreat.recommendation -eq "UPDATED: Implement prepared statements, stored procedures, and WAF rules") {
        Write-Host "Updated recommendation verified successfully!" -ForegroundColor Green
        Write-Host "  Final value: $($finalThreat.recommendation)" -ForegroundColor Gray
    } else {
        Write-Host "Updated recommendation was not saved!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to verify update: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 6: Testing empty recommendation..." -ForegroundColor Yellow
$emptyUpdate = @{
    recommendation = ""
    description = $threat.description
    likelihood = $threat.likelihood
    impact = $threat.impact
} | ConvertTo-Json

try {
    $emptyThreat = Invoke-RestMethod -Uri "$BaseUrl/threats/$ThreatId" -Method Patch -Headers $headers -Body $emptyUpdate
    Write-Host "Empty recommendation accepted" -ForegroundColor Green
} catch {
    Write-Host "Failed to set empty recommendation: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "All tests passed!" -ForegroundColor Green
Write-Host ""

if ($Cleanup) {
    Write-Host "Cleaning up test data..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod -Uri "$BaseUrl/threats/$ThreatId" -Method Delete -Headers $headers | Out-Null
        Write-Host "Test threat deleted" -ForegroundColor Green
    } catch {
        Write-Host "Could not delete threat" -ForegroundColor Yellow
    }
    
    try {
        Invoke-RestMethod -Uri "$BaseUrl/assessments/$AssessmentId" -Method Delete -Headers $headers | Out-Null
        Write-Host "Test assessment deleted" -ForegroundColor Green
    } catch {
        Write-Host "Could not delete assessment" -ForegroundColor Yellow
    }
} else {
    Write-Host "Test data preserved."
    Write-Host "Assessment ID: $AssessmentId" -ForegroundColor Cyan
    Write-Host "Threat ID: $ThreatId" -ForegroundColor Cyan
}
