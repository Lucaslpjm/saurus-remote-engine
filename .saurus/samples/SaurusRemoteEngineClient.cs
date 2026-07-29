using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace Saurus.Remote.Engine
{
    /// <summary>
    /// Cliente de referencia para o motor SaurusRemote.exe.
    /// Compativel com .NET Framework 4.7.2/C# 7.3 e .NET moderno.
    /// Operacoes administrativas devem ser delegadas a um helper elevado assinado.
    /// </summary>
    public sealed class SaurusRemoteEngineClient
    {
        public const string DefaultAccessPassword = "ophd0202";

        private static readonly Regex RemoteIdRegex =
            new Regex(@"^[0-9]{6,20}$", RegexOptions.CultureInvariant | RegexOptions.Compiled);

        private readonly string _enginePath;
        private readonly TimeSpan _commandTimeout;

        public SaurusRemoteEngineClient(string enginePath, TimeSpan? commandTimeout = null)
        {
            if (string.IsNullOrWhiteSpace(enginePath))
                throw new ArgumentException("O caminho do motor e obrigatorio.", nameof(enginePath));

            _enginePath = Path.GetFullPath(enginePath);
            _commandTimeout = commandTimeout ?? TimeSpan.FromSeconds(15);
        }

        public string EnginePath => _enginePath;

        public async Task<string> GetIdAsync(CancellationToken cancellationToken)
        {
            EngineCommandResult result = await RunAsync(
                "--get-id",
                standardInput: null,
                cancellationToken: cancellationToken).ConfigureAwait(false);

            result.EnsureSuccess("obter o ID");
            string[] lines = result.StandardOutput.Split(
                new[] { '\r', '\n' },
                StringSplitOptions.RemoveEmptyEntries);

            for (int index = lines.Length - 1; index >= 0; index--)
            {
                string candidate = lines[index].Trim().Replace(" ", string.Empty);
                if (RemoteIdRegex.IsMatch(candidate))
                    return candidate;
            }

            throw new InvalidOperationException("O motor nao retornou um ID numerico valido.");
        }

        public Task EnsureDefaultAccessPasswordAsync(CancellationToken cancellationToken)
        {
            return SetPermanentPasswordAsync(DefaultAccessPassword, cancellationToken);
        }

        /// <summary>
        /// Requer processo elevado e uma instalacao ativa do motor.
        /// A senha e enviada pelo stdin e nao aparece na linha de comando do Windows.
        /// </summary>
        public async Task SetPermanentPasswordAsync(
            string password,
            CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(password))
                throw new ArgumentException("A senha nao pode ser vazia.", nameof(password));
            if (password.Length < 8 || password.Length > 128)
                throw new ArgumentOutOfRangeException(nameof(password), "Use entre 8 e 128 caracteres.");
            if (!string.Equals(password, DefaultAccessPassword, StringComparison.Ordinal))
                throw new InvalidOperationException("O motor Saurus aceita somente a senha operacional padrão.");
            if (password.IndexOf('\0') >= 0 || password.IndexOf('\r') >= 0 || password.IndexOf('\n') >= 0)
                throw new ArgumentException("A senha contem caracteres de controle nao permitidos.", nameof(password));

            EngineCommandResult result = await RunAsync(
                "--password-stdin",
                password,
                cancellationToken).ConfigureAwait(false);

            result.EnsureSuccess("provisionar a senha permanente");
            if (result.StandardOutput.IndexOf("Done!", StringComparison.OrdinalIgnoreCase) < 0)
                throw new InvalidOperationException("O motor nao confirmou o provisionamento da senha.");
        }

        public Process Connect(string remoteId)
        {
            string id = NormalizeAndValidateRemoteId(remoteId);
            EnsureEngineExists();

            var startInfo = new ProcessStartInfo
            {
                FileName = _enginePath,
                Arguments = "--connect " + id,
                WorkingDirectory = Path.GetDirectoryName(_enginePath),
                UseShellExecute = false
            };

            Process process = Process.Start(startInfo);
            if (process == null)
                throw new InvalidOperationException("Nao foi possivel iniciar a sessao remota.");
            return process;
        }

        public static string NormalizeAndValidateRemoteId(string remoteId)
        {
            if (remoteId == null)
                throw new ArgumentNullException(nameof(remoteId));

            string normalized = remoteId.Replace(" ", string.Empty).Trim();
            if (!RemoteIdRegex.IsMatch(normalized))
                throw new FormatException("O ID remoto deve conter somente de 6 a 20 digitos.");
            return normalized;
        }

        private async Task<EngineCommandResult> RunAsync(
            string arguments,
            string standardInput,
            CancellationToken cancellationToken)
        {
            EnsureEngineExists();

            var startInfo = new ProcessStartInfo
            {
                FileName = _enginePath,
                Arguments = arguments,
                WorkingDirectory = Path.GetDirectoryName(_enginePath),
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = standardInput != null,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };

            using (var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true })
            {
                var exited = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
                process.Exited += (sender, args) => exited.TrySetResult(process.ExitCode);

                if (!process.Start())
                    throw new InvalidOperationException("Nao foi possivel iniciar o motor Saurus Remote.");

                Task<string> stdoutTask = process.StandardOutput.ReadToEndAsync();
                Task<string> stderrTask = process.StandardError.ReadToEndAsync();

                if (standardInput != null)
                {
                    await process.StandardInput.WriteAsync(standardInput).ConfigureAwait(false);
                    process.StandardInput.Close();
                }

                using (var timeoutCts = new CancellationTokenSource(_commandTimeout))
                using (var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(
                    cancellationToken,
                    timeoutCts.Token))
                using (linkedCts.Token.Register(() => exited.TrySetCanceled()))
                {
                    int exitCode;
                    try
                    {
                        exitCode = await exited.Task.ConfigureAwait(false);
                    }
                    catch (TaskCanceledException)
                    {
                        TryKill(process);
                        if (cancellationToken.IsCancellationRequested)
                            throw new OperationCanceledException(cancellationToken);
                        throw new TimeoutException(
                            "O motor nao respondeu dentro de " + _commandTimeout.TotalSeconds + " segundos.");
                    }

                    string stdout = await stdoutTask.ConfigureAwait(false);
                    string stderr = await stderrTask.ConfigureAwait(false);
                    return new EngineCommandResult(exitCode, stdout.Trim(), stderr.Trim());
                }
            }
        }

        private void EnsureEngineExists()
        {
            if (!File.Exists(_enginePath))
                throw new FileNotFoundException("Motor Saurus Remote nao encontrado.", _enginePath);
        }

        private static void TryKill(Process process)
        {
            try
            {
                if (!process.HasExited)
                    process.Kill();
            }
            catch
            {
                // O chamador recebera o timeout/cancelamento original.
            }
        }
    }

    public sealed class EngineCommandResult
    {
        public EngineCommandResult(int exitCode, string standardOutput, string standardError)
        {
            ExitCode = exitCode;
            StandardOutput = standardOutput ?? string.Empty;
            StandardError = standardError ?? string.Empty;
        }

        public int ExitCode { get; }
        public string StandardOutput { get; }
        public string StandardError { get; }

        public void EnsureSuccess(string operation)
        {
            if (ExitCode == 0 && string.IsNullOrWhiteSpace(StandardError))
                return;

            string detail = string.IsNullOrWhiteSpace(StandardError)
                ? StandardOutput
                : StandardError;
            throw new InvalidOperationException(
                "Falha ao " + operation + ". Codigo " + ExitCode + ". " + detail);
        }
    }
}
