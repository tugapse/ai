function test_server_flag() {
    $TEMP_OUT = New-TemporaryFile
    $REMOTE_TEMP_OUT = New-TemporaryFile
    $REMOTE_TASK_OUT = New-TemporaryFile
    $TEMP_TASK_FILE = New-TemporaryFile
    $REMOTE_SYS_OUT = New-TemporaryFile
    $TEMP_SYS_FILE = New-TemporaryFile
    $REMOTE_FILE_OUT = New-TemporaryFile
    $TEMP_FILE = New-TemporaryFile
    
    Write-Host "   [EXEC] $env:AI_CMD --server > `"$($TEMP_OUT.FullName)`" 2>&1 &"
    
    # Start server in background
    $serverProcess = Start-Process -FilePath "pwsh" -ArgumentList "-Command", "$env:AI_CMD --server > `"$($TEMP_OUT.FullName)`" 2>&1" -PassThru -WindowStyle Hidden
    
    # Wait 20 seconds for the server to initialize
    Write-Host "   [EXEC] Waiting 20 seconds for server to initialize..."
    Start-Sleep -Seconds 20
    
    if ($serverProcess.HasExited) {
        Write-Host "      -> ❌ FAILED: Server failed to start or crashed prematurely" -ForegroundColor Red
        Get-Content $TEMP_OUT.FullName -ErrorAction SilentlyContinue | Write-Host
        cleanup_files @($TEMP_OUT.FullName, $REMOTE_TEMP_OUT.FullName, $REMOTE_TASK_OUT.FullName, $TEMP_TASK_FILE.FullName, $REMOTE_SYS_OUT.FullName, $TEMP_SYS_FILE.FullName, $REMOTE_FILE_OUT.FullName, $TEMP_FILE.FullName)
        throw "Failed"
    }
    
    try {
        # Test Remote Connection
        Write-Host "   [EXEC] Testing remote connection: $env:AI_CMD --remote http://0.0.0.0:9999 -m `"Reply exactly with REMOTE_SUCCESS`" -o `"$($REMOTE_TEMP_OUT.FullName)`""
        Invoke-Expression "$env:AI_CMD -md default --remote http://0.0.0.0:9999 -m `"Reply exactly with REMOTE_SUCCESS`" -o `"$($REMOTE_TEMP_OUT.FullName)`""
        
        $content = Get-Content $REMOTE_TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "REMOTE_SUCCESS") {
             Write-Host "      -> Remote connection responded successfully" -ForegroundColor Green
        } else {
             Write-Host "      -> ❌ FAILED: Remote connection failed to respond correctly" -ForegroundColor Red
             Write-Host "      -> Content of remote output file ($($REMOTE_TEMP_OUT.FullName)):"
             if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
             throw "Failed"
        }
        
        # Test Remote Connection with Task File
        "Reply exactly with REMOTE_TASK_SUCCESS" | Set-Content -Path $TEMP_TASK_FILE.FullName
        Write-Host "   [EXEC] Testing remote connection with task file: $env:AI_CMD --remote http://0.0.0.0:9999 -tf `"$($TEMP_TASK_FILE.FullName)`" -o `"$($REMOTE_TASK_OUT.FullName)`""
        Invoke-Expression "$env:AI_CMD -md default --remote http://0.0.0.0:9999 -tf `"$($TEMP_TASK_FILE.FullName)`" -o `"$($REMOTE_TASK_OUT.FullName)`""
        
        $content = Get-Content $REMOTE_TASK_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "REMOTE_TASK_SUCCESS") {
             Write-Host "      -> Remote connection with task file responded successfully" -ForegroundColor Green
        } else {
             Write-Host "      -> ❌ FAILED: Remote connection with task file failed to respond correctly" -ForegroundColor Red
             Write-Host "      -> Content of remote output file ($($REMOTE_TASK_OUT.FullName)):"
             if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
             throw "Failed"
        }
        
        # Test Remote Connection with System File
        "You are a robot. Always reply exactly with REMOTE_SYS_SUCCESS." | Set-Content -Path $TEMP_SYS_FILE.FullName
        Write-Host "   [EXEC] Testing remote connection with system file: $env:AI_CMD --remote http://0.0.0.0:9999 -sf `"$($TEMP_SYS_FILE.FullName)`" -m `"Who are you?`" -o `"$($REMOTE_SYS_OUT.FullName)`""
        Invoke-Expression "$env:AI_CMD -md default --remote http://0.0.0.0:9999 -sf `"$($TEMP_SYS_FILE.FullName)`" -m `"Who are you?`" -o `"$($REMOTE_SYS_OUT.FullName)`""
        
        $content = Get-Content $REMOTE_SYS_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "REMOTE_SYS_SUCCESS") {
             Write-Host "      -> Remote connection with system file responded successfully" -ForegroundColor Green
        } else {
             Write-Host "      -> ❌ FAILED: Remote connection with system file failed to respond correctly" -ForegroundColor Red
             Write-Host "      -> Content of remote output file ($($REMOTE_SYS_OUT.FullName)):"
             if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
             throw "Failed"
        }

        # Test Remote Connection with Context File
        "SECRET_CODE_9999" | Set-Content -Path $TEMP_FILE.FullName
        Write-Host "   [EXEC] Testing remote connection with file: $env:AI_CMD --remote http://0.0.0.0:9999 -f `"$($TEMP_FILE.FullName)`" -m `"What is the secret code in the file? Output only the code.`" -o `"$($REMOTE_FILE_OUT.FullName)`""
        Invoke-Expression "$env:AI_CMD -md default --remote http://0.0.0.0:9999 -f `"$($TEMP_FILE.FullName)`" -m `"What is the secret code in the file? Output only the code.`" -o `"$($REMOTE_FILE_OUT.FullName)`""
        
        $content = Get-Content $REMOTE_FILE_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "SECRET_CODE_9999") {
             Write-Host "      -> Remote connection with file responded successfully" -ForegroundColor Green
        } else {
             Write-Host "      -> ❌ FAILED: Remote connection with file failed to respond correctly" -ForegroundColor Red
             Write-Host "      -> Content of remote output file ($($REMOTE_FILE_OUT.FullName)):"
             if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
             throw "Failed"
        }

    } finally {
        # Send SIGTERM-like shutdown, since PowerShell doesn't natively do SIGTERM to child we will kill the process tree.
        Write-Host "   [EXEC] Stopping process tree of server"
        taskkill /PID $serverProcess.Id /T /F | Out-Null
        
        # Wait for log flush (not strictly guaranteed after taskkill, but let's check what we have)
        Start-Sleep -Seconds 2
        
        $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "(?i)graceful shutdown") {
            Write-Host "      -> Server Flag successfully verified (Started and Stopped cleanly)" -ForegroundColor Green
            cleanup_files @($TEMP_OUT.FullName, $REMOTE_TEMP_OUT.FullName, $REMOTE_TASK_OUT.FullName, $TEMP_TASK_FILE.FullName, $REMOTE_SYS_OUT.FullName, $TEMP_SYS_FILE.FullName, $REMOTE_FILE_OUT.FullName, $TEMP_FILE.FullName)
        } else {
            Write-Host "      -> ❌ FAILED: Server did not log graceful shutdown" -ForegroundColor Red
            Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
            if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
            cleanup_files @($TEMP_OUT.FullName, $REMOTE_TEMP_OUT.FullName, $REMOTE_TASK_OUT.FullName, $TEMP_TASK_FILE.FullName, $REMOTE_SYS_OUT.FullName, $TEMP_SYS_FILE.FullName, $REMOTE_FILE_OUT.FullName, $TEMP_FILE.FullName)
            throw "Failed"
        }
    }
}

function run_category_5() {
    Write-Host "`n### Category 5: Blocking / Long-Running Processes ###" -ForegroundColor Green
    run_test "Server Flag (--server)" "Verifies the AI server starts in the background and shuts down gracefully upon SIGTERM." "test_server_flag"
}