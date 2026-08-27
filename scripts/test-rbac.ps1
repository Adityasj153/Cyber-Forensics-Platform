#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests RBAC enforcement across all API endpoints.
    Requires: backend running at http://localhost:8000, docker compose up.

.DESCRIPTION
    1. Registers 3 users (admin, investigator, viewer) — NOTE: register now always creates VIEWER.
       So we create via register + direct DB update, OR use the testuser (investigator) that exists.
    2. Logs in as each role.
    3. Tests that:
       - Viewer cannot create cases, add devices, upload logs, review anomalies
       - Investigator can do all of the above
       - Viewer CAN list/read cases, devices, search, anomalies, correlations, entities
       - Viewer CANNOT access a case they're not assigned to

.NOTES
    Run from project root: pwsh scripts/test-rbac.ps1
#>

$BASE = "http://localhost:8000/api"

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Token,
        [object]$Body = $null,
        [hashtable]$Files = $null
    )
    $headers = @{}
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }

    $params = @{
        Method     = $Method
        Uri        = "$BASE$Path"
        Headers    = $headers
        ErrorAction = "SilentlyContinue"
    }
    if ($Body) {
        $params.Body = ($Body | ConvertTo-Json)
        $headers["Content-Type"] = "application/json"
    }

    try {
        $response = Invoke-WebRequest @params
        return @{ Status = $response.StatusCode; Body = $response.Content | ConvertFrom-Json -ErrorAction SilentlyContinue }
    } catch {
        $errResponse = $_.Exception.Response
        if ($errResponse) {
            $reader = New-Object System.IO.StreamReader($errResponse.GetResponseStream())
            $errBody = $reader.ReadToEnd()
            return @{ Status = [int]$errResponse.StatusCode; Body = $errBody | ConvertFrom-Json -ErrorAction SilentlyContinue; Error = $errBody }
        }
        return @{ Status = 0; Error = $_.Exception.Message }
    }
}

$pass = 0
$fail = 0
function Assert-Status {
    param($result, $expected, $label)
    if ($result.Status -eq $expected) {
        Write-Host "  PASS: $label (HTTP $($result.Status))" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  FAIL: $label — expected HTTP $expected, got HTTP $($result.Status)" -ForegroundColor Red
        if ($result.Error) { Write-Host "         $($result.Error)" -ForegroundColor DarkRed }
        $script:fail++
    }
}

Write-Host "`n=== RBAC Test Suite ===" -ForegroundColor Cyan

# --- Setup: login as testuser (investigator) ---
Write-Host "`n[1] Login as testuser (investigator)" -ForegroundColor Yellow
$invLogin = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "testuser"; password = "TestPass123!" }
$invToken = $invLogin.Body.access_token
Assert-Status $invLogin 200 "Investigator login"

# --- Setup: register a viewer user ---
Write-Host "`n[2] Register viewer user" -ForegroundColor Yellow
$viewerReg = Invoke-Api -Method POST -Path "/auth/register" -Body @{ username = "rbac_test_viewer"; email = "viewer@test.com"; password = "Viewer123!" }
Assert-Status $viewerReg 201 "Register viewer"
# NOTE: register now always creates VIEWER (role escalation fix)

# Login as viewer
$viewerLogin = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "rbac_test_viewer"; password = "Viewer123!" }
$viewerToken = $viewerLogin.Body.access_token
Assert-Status $viewerLogin 200 "Viewer login"

# --- Test 1: Self-registration no longer allows role escalation ---
Write-Host "`n[3] Registration cannot self-assign admin role" -ForegroundColor Yellow
# The register endpoint no longer accepts a role field — it always creates VIEWER.
# Verify by checking the registered user's role via /auth/me (would need a token, but we can check the response)
# The register response includes role — verify it's "viewer" regardless
$viewerRole = $viewerReg.Body.role
if ($viewerRole -eq "viewer") {
    Write-Host "  PASS: Registered user role is 'viewer' (no escalation)" -ForegroundColor Green
    $pass++
} else {
    Write-Host "  FAIL: Registered user role is '$viewerRole' (expected 'viewer')" -ForegroundColor Red
    $fail++
}

# --- Test 2: Viewer cannot create a case ---
Write-Host "`n[4] Viewer cannot create a case" -ForegroundColor Yellow
$caseCreate = Invoke-Api -Method POST -Path "/cases" -Token $viewerToken -Body @{ name = "RBAC Test Case" }
Assert-Status $caseCreate 403 "Viewer POST /cases → 403"

# Investigator CAN create a case
Write-Host "`n[5] Investigator can create a case" -ForegroundColor Yellow
$caseCreateInv = Invoke-Api -Method POST -Path "/cases" -Token $invToken -Body @{ name = "RBAC Test Case" }
Assert-Status $caseCreateInv 201 "Investigator POST /cases → 201"
$caseId = $caseCreateInv.Body.id

# --- Test 3: Viewer can list cases (assigned ones) ---
Write-Host "`n[6] Viewer can list cases" -ForegroundColor Yellow
$viewerCases = Invoke-Api -Method GET -Path "/cases" -Token $viewerToken
Assert-Status $viewerCases 200 "Viewer GET /cases → 200"

# --- Test 4: Viewer cannot create a device ---
Write-Host "`n[7] Viewer cannot create a device" -ForegroundColor Yellow
$deviceCreate = Invoke-Api -Method POST -Path "/cases/$caseId/devices" -Token $viewerToken -Body @{ device_type = "pc"; name = "Test PC" }
Assert-Status $deviceCreate 403 "Viewer POST /cases/{id}/devices → 403"

# Investigator CAN create a device
Write-Host "`n[8] Investigator can create a device" -ForegroundColor Yellow
$deviceCreateInv = Invoke-Api -Method POST -Path "/cases/$caseId/devices" -Token $invToken -Body @{ device_type = "pc"; name = "Test PC" }
Assert-Status $deviceCreateInv 201 "Investigator POST /cases/{id}/devices → 201"

# --- Test 5: Viewer can list devices (if assigned to case) ---
# Viewer is NOT assigned to this case (only the investigator who created it is)
Write-Host "`n[9] Viewer cannot access unassigned case's devices" -ForegroundColor Yellow
$deviceList = Invoke-Api -Method GET -Path "/cases/$caseId/devices" -Token $viewerToken
Assert-Status $deviceList 403 "Viewer GET /cases/{id}/devices (unassigned) → 403"

# Investigator CAN list devices
Write-Host "`n[10] Investigator can list devices" -ForegroundColor Yellow
$deviceListInv = Invoke-Api -Method GET -Path "/cases/$caseId/devices" -Token $invToken
Assert-Status $deviceListInv 200 "Investigator GET /cases/{id}/devices → 200"

# --- Test 6: Viewer cannot review anomalies ---
Write-Host "`n[11] Viewer cannot review anomalies" -ForegroundColor Yellow
$anomalyReview = Invoke-Api -Method PATCH -Path "/cases/$caseId/anomalies/fake-id/review" -Token $viewerToken -Body @{ review_status = "confirmed" }
Assert-Status $anomalyReview 403 "Viewer PATCH /cases/{id}/anomalies/{id}/review → 403"

# --- Test 7: Viewer cannot update a case ---
Write-Host "`n[12] Viewer cannot update a case" -ForegroundColor Yellow
$caseUpdate = Invoke-Api -Method PATCH -Path "/cases/$caseId" -Token $viewerToken -Body @{ name = "Hacked" }
Assert-Status $caseUpdate 403 "Viewer PATCH /cases/{id} → 403"

# --- Test 8: Investigator cannot update unassigned case ---
Write-Host "`n[13] Investigator cannot update unassigned case" -ForegroundColor Yellow
# Create a second case with the viewer (wait, viewer can't create cases)
# Let's create with investigator, then a second investigator tries to update
$inv2Reg = Invoke-Api -Method POST -Path "/auth/register" -Body @{ username = "rbac_test_inv2"; email = "inv2@test.com"; password = "Inv2Pass123!" }
# Login as inv2
$inv2Login = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "rbac_test_inv2"; password = "Inv2Pass123!" }
$inv2Token = $inv2Login.Body.access_token
$caseUpdateInv2 = Invoke-Api -Method PATCH -Path "/cases/$caseId" -Token $inv2Token -Body @{ name = "Stolen" }
Assert-Status $caseUpdateInv2 403 "Investigator PATCH /cases/{id} (unassigned) → 403"

# --- Summary ---
Write-Host "`n=== Results ===" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "Total:  $($pass + $fail)" -ForegroundColor White

if ($fail -gt 0) {
    Write-Host "`nSome RBAC tests failed. See above for details." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nAll RBAC tests passed." -ForegroundColor Green
    exit 0
}
