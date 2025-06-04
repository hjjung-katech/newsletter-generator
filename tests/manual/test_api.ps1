# PowerShell script to test the newsletter API
Write-Host "🧪 Testing Newsletter Generator Web API" -ForegroundColor Green

$baseUrl = "http://localhost:5000"
$testData = @{
    keywords = "AI,자율주행"
    template_style = "compact"
    email_compatible = $false
    period = 7
} | ConvertTo-Json

Write-Host "📋 Test parameters:" -ForegroundColor Cyan
Write-Host "   Keywords: AI,자율주행"
Write-Host "   Template style: compact"
Write-Host "   Email compatible: false"
Write-Host "   Period: 7 days"

try {
    Write-Host "`n🔍 Checking server availability..." -ForegroundColor Yellow
    $healthCheck = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -TimeoutSec 5
    Write-Host "✅ Server is running" -ForegroundColor Green
    
    Write-Host "`n🚀 Starting newsletter generation..." -ForegroundColor Yellow
    $startTime = Get-Date
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/generate" -Method Post -Body $testData -ContentType "application/json" -TimeoutSec 300
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    Write-Host "⏱️  Request completed in $([math]::Round($duration, 2)) seconds" -ForegroundColor Green
    Write-Host "✅ Newsletter generation successful!" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor White
    Write-Host "   Subject: $($response.subject)" -ForegroundColor White
    Write-Host "   Content length: $($response.html_content.Length)" -ForegroundColor White
    Write-Host "   Articles count: $($response.articles_count)" -ForegroundColor White
    
    # Check if it's using real CLI or mock
    if ($response.cli_output) {
        $cliPreview = $response.cli_output.Substring(0, [Math]::Min(200, $response.cli_output.Length))
        Write-Host "   CLI output (first 200 chars): $cliPreview..." -ForegroundColor White
        Write-Host "🎯 Using RealNewsletterCLI successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No CLI output detected - likely using Mock" -ForegroundColor Yellow
    }
    
    # Save result for inspection
    $response.html_content | Out-File -FilePath "test_newsletter_result.html" -Encoding UTF8
    Write-Host "💾 Newsletter saved to test_newsletter_result.html" -ForegroundColor Green
    
    Write-Host "`n🎉 Test completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Message -like "*ConnectFailure*" -or $_.Exception.Message -like "*timeout*") {
        Write-Host "   Make sure Flask server is running: python web\app.py" -ForegroundColor Yellow
    }
}
