function test_simple_message() {
    $TEMP_OUT = New-TemporaryFile
    Write-Host "   [EXEC] $env:AI_CMD -m `"Hello`" -o `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -m `"Hello`" -o `"$($TEMP_OUT.FullName)`""
    $exit_code = $LASTEXITCODE
    
    if ($exit_code -eq 0 -or $exit_code -eq $null) {
        Write-Host "      -> Simple Message successfully executed" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Simple Message execution failed" -ForegroundColor Red
        cleanup_files @($TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT.FullName)
}

function test_file_flag() {
    $TEMP_FILE = New-TemporaryFile
    $TEMP_OUT = New-TemporaryFile
    "SECRET_CODE_4285" | Set-Content -Path $TEMP_FILE.FullName
    
    Write-Host "   [EXEC] $env:AI_CMD -f `"$($TEMP_FILE.FullName)`" -m `"What is the secret code in the file? Output only the code.`" -o `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -f `"$($TEMP_FILE.FullName)`" -m `"What is the secret code in the file? Output only the code.`" -o `"$($TEMP_OUT.FullName)`""
    
    $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "SECRET_CODE_4285") {
        Write-Host "      -> File Flag successfully verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: File Flag verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_FILE.FullName, $TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_FILE.FullName, $TEMP_OUT.FullName)
}

function test_task_flag() {
    $TEMP_TASK_OUT = New-TemporaryFile
    $taskDir = Join-Path $env:AI_ASSISTANT_DIRECTORY "task"
    if (-not (Test-Path $taskDir)) { New-Item -ItemType Directory -Path $taskDir | Out-Null }
    $TASK_FILE = Join-Path $taskDir "secret_task.md"
    "Reply exactly with the secret code: SECRET_CODE_7777" | Set-Content -Path $TASK_FILE
    
    Write-Host "   [EXEC] $env:AI_CMD -t `"secret_task`" -o `"$($TEMP_TASK_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -t `"secret_task`" -o `"$($TEMP_TASK_OUT.FullName)`""
    
    $content = Get-Content $TEMP_TASK_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "SECRET_CODE_7777") {
        Write-Host "      -> Task output file successfully created and verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Task output file not created or verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_TASK_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_TASK_OUT.FullName, $TASK_FILE)
        throw "Failed"
    }
    cleanup_files @($TEMP_TASK_OUT.FullName, $TASK_FILE)
}

function test_task_file_flag() {
    $TEMP_TASK_FILE = New-TemporaryFile
    $TEMP_TASK_OUT = New-TemporaryFile
    "Reply exactly with the secret code: SECRET_CODE_8888" | Set-Content -Path $TEMP_TASK_FILE.FullName
    
    Write-Host "   [EXEC] $env:AI_CMD -tf `"$($TEMP_TASK_FILE.FullName)`" -o `"$($TEMP_TASK_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -tf `"$($TEMP_TASK_FILE.FullName)`" -o `"$($TEMP_TASK_OUT.FullName)`""
    
    $content = Get-Content $TEMP_TASK_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "SECRET_CODE_8888") {
        Write-Host "      -> Task output file successfully created and verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Task output file not created or verification failed" -ForegroundColor Red
        Write-Host "      -> Task input file was: $($TEMP_TASK_FILE.FullName)"
        Write-Host "      -> Content of output file ($($TEMP_TASK_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_TASK_FILE.FullName, $TEMP_TASK_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_TASK_FILE.FullName, $TEMP_TASK_OUT.FullName)
}

function run_category_2() {
    Write-Host "`n### Category 2: Single-Turn Execution ###" -ForegroundColor Green
    run_test "Simple Message (-m)" "Validates that a direct message query processes correctly and exits cleanly." "test_simple_message"
    run_test "Task Flag (-t)" "Checks if a predefined task template is located and executed properly." "test_task_flag"
    run_test "File Flag (-f)" "Tests the ability to read context from a file and answer a query about it." "test_file_flag"
    run_test "Task File Flag (-tf)" "Verifies that a custom task file is loaded and used to generate correct output." "test_task_file_flag"
}
