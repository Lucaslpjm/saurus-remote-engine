using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Saurus Remote Launcher")]
[assembly: System.Reflection.AssemblyProduct("Saurus Remote")]
[assembly: System.Reflection.AssemblyCompany("Saurus Software")]
[assembly: System.Reflection.AssemblyCopyright("Copyright (c) Saurus Software")]

internal static class SaurusRemoteLauncher
{
    private const string EngineFileName = "SaurusRemote.exe";

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string installDirectory = AppDomain.CurrentDomain.BaseDirectory;
            string enginePath = Path.Combine(installDirectory, EngineFileName);
            if (!File.Exists(enginePath))
            {
                MessageBox.Show(
                    "O executavel principal do Saurus Remote nao foi encontrado.",
                    "Saurus Remote",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return 2;
            }

            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = enginePath,
                Arguments = BuildArguments(args),
                WorkingDirectory = installDirectory,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(startInfo);
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(
                "Nao foi possivel abrir o Saurus Remote.\r\n\r\n" + error.Message,
                "Saurus Remote",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string BuildArguments(string[] args)
    {
        if (args == null || args.Length == 0)
        {
            return string.Empty;
        }

        StringBuilder commandLine = new StringBuilder();
        foreach (string argument in args)
        {
            if (commandLine.Length > 0)
            {
                commandLine.Append(' ');
            }
            commandLine.Append(QuoteArgument(argument ?? string.Empty));
        }
        return commandLine.ToString();
    }

    // Implements the quoting rules consumed by CommandLineToArgvW.
    private static string QuoteArgument(string argument)
    {
        if (argument.Length > 0 && argument.IndexOfAny(new[] { ' ', '\t', '\n', '\v', '"' }) < 0)
        {
            return argument;
        }

        StringBuilder quoted = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char character in argument)
        {
            if (character == '\\')
            {
                backslashes++;
                continue;
            }

            if (character == '"')
            {
                quoted.Append('\\', (backslashes * 2) + 1);
                quoted.Append('"');
                backslashes = 0;
                continue;
            }

            quoted.Append('\\', backslashes);
            backslashes = 0;
            quoted.Append(character);
        }

        quoted.Append('\\', backslashes * 2);
        quoted.Append('"');
        return quoted.ToString();
    }
}
