package main

import (
    "fmt"
    "os"
	"os/exec"
    "path/filepath"
	"strings"
	"bytes"
)

// arg is start-path.

func convert() filepath.WalkFunc {
    return func(path string, info os.FileInfo, err error) error {
        if err != nil {
            return nil
        }
		if info.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".docx" {
			return nil
		}
		fmt.Println(path)
        //convertFile(fileNameWithoutExtension(filepath.Base(path)), filepath.Dir(path), "C:/Hugo/Sites/Life For         convertFile("What Christ has done for us - Interactive preach", "C:/Users/Stephen/Documents/Church_Teaching/Organic Church", "C:/Hugo/Sites/Life For Liberia/static/pandoc" )
        return nil
    }
}

func main() {
convertFile("What Christ has done for us - Interactive preach", "C:\\Users\\Stephen\\Documents\\Church_Teaching\\Organic Church", "C:\\Hugo\\Sites\\Life For Liberia\\static\\pandoc" )
	//if checkAppExists("pandoc") {
		//root := os.Args[1]
		//err := filepath.Walk(root, convert())
		//if err != nil {
			//panic(err)
		//}
	//}
}

func fileNameWithoutExtension(fileName string) string {
	return strings.TrimSuffix(fileName, filepath.Ext(fileName))
}

func convertFile(file string, inPath string, outPath string) {
	infile := "\"" + inPath + "\\" + file + ".docx\""
	outfile := "\"" + outPath + "\\" + file + ".md\""
	cmd := exec.Command("pandoc", "-s", "-f", "docx", infile , "-t", "markdown", "-o", outfile )
	fmt.Println(cmd.Args)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	err := cmd.Run()
	if err != nil {
		fmt.Println(fmt.Sprint(err) + ": " + stderr.String())
	}
}

func checkAppExists(appName string) bool {
    _ , err := exec.LookPath(appName)
    if err != nil {
        fmt.Printf("didn't find " + appName + " executable\n")
		return false
    }
	return true
}