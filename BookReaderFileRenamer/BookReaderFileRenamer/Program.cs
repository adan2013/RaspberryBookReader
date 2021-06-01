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

        static void Main(string[] args)
        {
            if (args.Length > 0)
            {
                string dirPath = args[0];
                if(Directory.Exists(dirPath))
                {
                    DirectoryInfo dirInfo = new DirectoryInfo(dirPath);
                    FileInfo[] files = dirInfo.GetFiles().OrderBy(p => p.Name).ToArray();
                    for (int i = 0; i < files.Length; i++)
                    {
                        FileInfo file = files[i];
                        Console.WriteLine(file.Name + " >>> " + generateFileName(i));
                    }
                    Console.WriteLine("Type \"yes\" to accept this file names: ");
                    string answer = Console.ReadLine();
                    if(answer == "yes")
                    {
                        for (int i = 0; i < files.Length; i++)
                        {
                            files[i].MoveTo(Path.Combine(dirPath, generateFileName(i)));
                        }
                        Console.WriteLine("Done! Files renamed successfully!");
                    }
                    else
                    {
                        Console.WriteLine("Operation abort!");
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
