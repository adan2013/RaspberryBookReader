using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace BookReaderFileRenamer
{
    class Program
    {
        static string generateFileName(int index)
        {
            index++;
            if (index > 99) return index.ToString() + ".mp3";
            if (index > 9) return "0" + index.ToString() + ".mp3";
            return "00" + index.ToString() + ".mp3";
        }

        static void renameFilesInDirectory(string path)
        {
            Console.WriteLine("------------------------------");
            DirectoryInfo dirInfo = new DirectoryInfo(path);
            FileInfo[] files = dirInfo.GetFiles().Where(p => p.Extension == ".mp3").OrderBy(p => p.Name).ToArray();
            if(files.Length == 0)
            {
                Console.WriteLine("Directory: " + path);
                Console.WriteLine("Directory doesn't contain any files!");
            }
            else
            {
                for (int i = 0; i < files.Length; i++)
                {
                    FileInfo file = files[i];
                    Console.WriteLine(file.Name + " >>> " + generateFileName(i));
                }
                Console.WriteLine("------------------------------");
                Console.WriteLine("Directory: " + path);
                Console.WriteLine("Type \"yes\" to accept this file names: ");
                string answer = Console.ReadLine();
                if (answer == "yes")
                {
                    for (int i = 0; i < files.Length; i++)
                    {
                        files[i].MoveTo(Path.Combine(path, generateFileName(i)));
                    }
                    Console.WriteLine("Done! Files renamed successfully!");
                }
                else
                {
                    Console.WriteLine("Operation abort!");
                }
            }
        }

        static void Main(string[] args)
        {
            if (args.Length > 0)
            {
                string dirPath = args[0];
                if(Directory.Exists(dirPath))
                {
                    renameFilesInDirectory(dirPath);
                    DirectoryInfo dirInfo = new DirectoryInfo(dirPath);
                    DirectoryInfo[] directories = dirInfo.GetDirectories().OrderBy(p => p.Name).ToArray();
                    if(directories.Length > 0)
                    {
                        Console.WriteLine("------------------------------");
                        Console.WriteLine("Running recursive search...");
                        for (int i = 0; i < directories.Length; i++)
                        {
                            DirectoryInfo d = directories[i];
                            renameFilesInDirectory(d.FullName);
                        }
                    }
                }
                else
                {
                    Console.WriteLine("Directory not exists!");
                }
            }
            else
            {
                Console.WriteLine("Invalid directory path!");
            }
            Console.ReadKey();
        }
    }
}
