#pip install windows-curses
from curses.ascii import isalpha, isdigit
from pathlib import Path
from datetime import datetime
import subprocess
from xml.dom.minidom import Element # for git
import ctypes # To prevent windows sleep
# Install deep_translator with: 
# python.exe -m pip install --upgrade pip
# pip install -U deep-translator
from deep_translator import GoogleTranslator
import ctypes
import os
# pip install --upgrade pywin32 
# pip install --upgrade deepl # get free api key for deep-language translator.
import win32com
from win32com.client import constants
# pip install pandoc
#import pypandoc
#import mammoth
# pip install aspose.words # $1200 for full version!
#import aspose.words as aw
#import deepl

#auth_key = "b2937538-9e72-61ff-03f0-e76261dc273a:fx"
#translator = deepl.Translator(auth_key)

#pandocCmd = "pandoc"
#docxToPdfCmd = r"C:\Hugo\docto105\docto"
toc_tag = "](#"
REDO_PDFS = False
word = None
word_template = None
do_translations = True
# Toml INI files
def readINI() :
  docxRoot = Path.cwd() 
  iniPath = docxRoot / "docxToHugo.toml"
  webRootPath = docxRoot.parent
  dotxTemplate = "Kingdom-Apprentices_Styles.dotx"
  sourceLanguage = 'en'
  languages = ['en']
  dateChanged = True
  if iniPath.exists() :
      iniFileDate = datetime.fromtimestamp(iniPath.stat().st_mtime)
      with iniPath.open('r', encoding="utf-8") as iniFile:
        for line in iniFile:
          line = line.strip()
          if line == "[Hugo Website Root]":
            webRootPath = Path(iniFile.readline().strip('\t\n "\''))
          if line == "[Docx Root]":
            docxRoot = Path(iniFile.readline().strip('\t\n "\''))
          if line == "[Docx Language]":
            sourceLanguage = iniFile.readline().strip('\t\n "\'')
          if line == "[Dotx Template Path]":
            dotxTemplate = iniFile.readline().strip('\t\n "\'')
          if line == "[Languages]":
            languages = iniFile.readline().strip('[] \t\n').replace(' ', '').split(',')
          if line == "[DateChanged]":
            dateChanged = datetime.fromisoformat(iniFile.readline().strip(' \t\n'))     
      iniFile.close()
      if (iniFileDate - dateChanged).total_seconds() > 0:
        dateChanged = True
      else:  dateChanged = False              
  if dateChanged: updateINI(iniPath, webRootPath, docxRoot, dotxTemplate, sourceLanguage, languages)
  return iniPath, webRootPath, docxRoot, dotxTemplate, sourceLanguage, languages, dateChanged

def updateINI(iniFile, webRoot, docxRoot, dotxTemplate, sourceLanguage, languages):
  with iniFile.open('w', encoding="utf-8") as ini: 
    ini.write("[Hugo Website Root]\n   ")
    ini.write(str(webRoot))    
    ini.write("\n[Docx Root]\n   ")
    ini.write(str(docxRoot))
    ini.write("\n[Docx Language]\n   ")
    ini.write(sourceLanguage)    
    ini.write("\n[Dotx Template Path]\n   ")
    ini.write(dotxTemplate)    
    ini.write("\n[Languages]\n   ")
    languages = str(languages).replace("'","")
    languages = languages.replace(" ","")
    ini.write(languages)
    ini.write("\n[DateChanged]\n   ")
    ini.write(str(datetime.now()))

# Windows functions
def Msgbox(title, text, style):
    # Style 0:OK; 1:OK,Cancel; 3:Y/N/Cancel; 4:Y/N
    # Reply: 1:OK; 2:Cancel; 6:Y; 7:N
    return ctypes.windll.user32.MessageBoxW(0, str(text), str(title), style)

# File-system
def pathToURL(path):
  path = str(path).replace(' ','-')
  path = path.replace('\\','/')
  for char in path:
    if not char.isalnum():
      if char not in (':','/','-','_','.','~'):
        path = path.replace(char,'')
        
  while path.find('--') >= 0:
    path = path.replace('--','-')
  return path

def sourceDocName(sourcePath):
  sourceDocStart = sourcePath.stem.find('_')
  sourceDocName = sourcePath.stem[sourceDocStart + 1:]
  return sourcePath.parent / (sourceDocName + sourcePath.suffix)

def pdf_in_md_folder(dirItem):
  if dirItem.suffix != '.pdf' : return False
  md_folder = dirItem.parent.parent
  return list(md_folder.glob(f'{dirItem.stem}_*.md'))

def deleteAll(path, pattern):
  if path.exists():
    if path.is_file():
      path.unlink()
    else:
      pattern = '**/' + f'*{pattern}*'.replace('**','*')
      for item in path.rglob(pattern):
        if item.is_file():
          item.unlink()
      
    # Recursively delete empty directories
    for dir_path in reversed(list(path.glob('**/'))):
        try:
            dir_path.rmdir()
        except OSError:
            # Directory is not empty
            pass

    if path.suffix != '': path = path.parent
    remainingFiles = list(path.rglob('*'))
    if len(remainingFiles) == 1 and remainingFiles[0].name == '_index.md':
      remainingFiles[0].unlink()
      del remainingFiles[0]
    
    if path.exists() and len(remainingFiles) == 0:
       path.rmdir()
      
  
def deleteRemovedFiles(docSourceRootPath, mdSourceRootPath: Path, contentPath, languages):
  # If a source.md is missing from source.docx, delete the entire content.md & media folder in all languages
  startPath = len(str(mdSourceRootPath))
  for dirItem in sorted(mdSourceRootPath.rglob('*')):
    if dirItem.stem[0] == '~' : continue
    subItem = str(dirItem)[startPath+1:]
    sourceItem = docSourceRootPath / subItem
    if dirItem.is_file():
      sourceItem = sourceItem.with_suffix('.docx')
      print(f'Check: {sourceItem.name}')
      pass
    if not sourceItem.exists():
      deleteAll(dirItem,'')
      pathStr = str(mdSourceRootPath) + '\\'
      doc_media = Path(pathStr.replace('\\en\\','\\media\\'))
      subItem = Path(pathToURL(subItem))
      deleteAll(doc_media / subItem.with_suffix(''),'')
      file = subItem.stem
      if subItem.suffix != '': subItem = subItem.parent

      for lang in languages: 
        mdLangPath = contentPath / lang
        deleteAll(mdLangPath/subItem, file)

def fileNeedsUpdating(sourceFile, convertedFile):
  if convertedFile.exists():
    convertedFileDate = datetime.fromtimestamp(convertedFile.stat().st_mtime)
    sourceFileDate = datetime.fromtimestamp(sourceFile.stat().st_mtime)
    timeDiff = (sourceFileDate - convertedFileDate).total_seconds() 
    fileOutOfDate = timeDiff > 60
  else:
    fileOutOfDate = True
  return fileOutOfDate

def mdFiles_missing(langMDpath, docName):
  langFiles = list(langMDpath.rglob(f'*{docName}*.md'))
  if len(langFiles) == 0: return True
  return False

def haveMadeNewFolder(folder) :
  if not folder.exists():
    folder.mkdir(parents=True)
    return True
  return False

def createMDfolder(mdDestinationPath, language, sourceLanguage) :
    haveMadeNewFolder(mdDestinationPath)
    outerFolder = mdDestinationPath
    while haveCreatedNewMDindex(outerFolder, language, sourceLanguage):
      outerFolder = outerFolder.parent

def get_leading_digits(input_string):
  endPos = next((i for i, char in enumerate(input_string) if not char.isdigit()), -1)
  return input_string[0:endPos],input_string[endPos:]

def haveCreatedNewMDindex(mdDestinationPath, language, sourceLanguage):
  DirectoryName = mdDestinationPath.name
  if DirectoryName == "content" or DirectoryName == language:
    needsIndex = False
  else:
    filePath = mdDestinationPath / "_index.md"
    needsIndex = not filePath.exists()
    if needsIndex:
      weight,lang_title = get_leading_digits(DirectoryName)
      lang_title = lang_title.lstrip('_')
      with filePath.open('w', encoding="utf-8") as writeFile:
        if language != sourceLanguage:
          lang_title = translateBlock(lang_title,language)
 
        header = create_frontMatter(weight, DirectoryName, 'document-folder', lang_title,"")  
        writeFile.write(header)
  return needsIndex

def addSummaryTo_index(langMDpath, summary):
  # file.truncate() doesn't seem to work!!!
  indexFile = langMDpath/ "_index.md"
  if indexFile.exists():
    frontMatter = []
    with indexFile.open('r', encoding="utf-8") as read_File:
      frontMatter.append(read_File.readline())
      for line in read_File:
        frontMatter.append(line)
        if line[:3] == '---': break

    with indexFile.open('w', encoding="utf-8") as write_File:
      for line in frontMatter:
        write_File.write(line)

      write_File.write(summary)

def savePageAs_md(page, filePath):
  try:
    word.Documents.Close(SaveChanges=-1)
  except:
    pass
  with filePath.open('w', encoding="utf-8") as md_file: 
    for line in page:
      md_file.write(line)

def file_repair_TOC(lang_file):
  with lang_file.open('r', encoding="utf-8") as original:
      tempFile = lang_file.parent / 'tempFile.txt'
      with tempFile.open('w', encoding="utf-8") as temp: 
        for line in original:
          labelStart, tocStart, tocEnd = toc_pos(line,0)
          if labelStart > 0:
            line = repair_TOC(line, labelStart, tocStart, tocEnd)
          
          temp.write(line)

      original.close()
      lang_file.unlink()
      temp.close()
      tempFile.replace(lang_file)  
  
# General File Modification
charmap = { 0x201c : u"'",
            0x201d : u"'",
            0x2018 : u"'",
            0x2019 : u"'" }
def convertFromSmartQuotes(line):
  return line.translate(charmap) if type(line) is str else line
'''
def strip_lines_from_File(originalfile, search_string):
    with originalfile.open('r', encoding="utf-8") as original:
      tempFile = originalfile.parent / 'tempFile.txt'

      with tempFile.open('w', encoding="utf-8") as temp: 
        for line in original:
          if line.find(search_string) == -1:
            temp.write(line)

      original.close()
      originalfile.unlink()
      temp.close()
      tempFile.replace(originalfile)
'''
def prependToPage(page, string):
  if not page[0].startswith('# '):
    string += '\n'
  page.insert(0,str(string))

def combinedMD_to_pages(docAsMD):
  with docAsMD.open('r', encoding="utf-8") as originalfile:
    pages = [[]] # list of pages, each page is list of lines
    pageNo = -1
    gotFirst_H1_2 = False
    inTOC = -1
    doingSummary = False
    # Start appending lines when get past initial bold and TOC.
    for line in originalfile:
      gotContent = True
      if len(line) < 6: gotContent = False
      if gotContent and inTOC:
        if line.startswith('['):
          inTOC = 1
          continue
          
        if inTOC == 1 and line[0].isalnum():
          inTOC = 0
        elif line.startswith('#'):
          inTOC = 0
        else:
          continue

      if gotContent and not gotFirst_H1_2:
        if line[0:4] == '### ': # H3 Summary before H1/2
          doingSummary = True
          pageNo = 0
        elif line[0] == '#': # H1/2 so stop summary
          gotFirst_H1_2 = True
          doingSummary = False
          pageNo += 1
          if len(pages) < pageNo + 1:
            pages.append([])
        elif not doingSummary: # Text before heading
          doingSummary = True
          pageNo = 0
          #pages[pageNo].append('###\n')
      elif gotContent and line[0:2] == '# ': # New H1, so create new page
        pageNo += 1
        pages.append([])

      if pageNo >=0: pages[pageNo].append(line)

    if pageNo == -1:
      originalfile.seek(0)
      pageNo = 0
      for line in originalfile:
        pages[0].append(line)
      
  return pages

# Image processing
def imageTag(line):
  # test endNamePos > 0 for found image
  startNamePos = line.find('![')
  if startNamePos >= 0:
    startNamePos += 2
    endNamePos = line.find(']',startNamePos)
    if endNamePos >= startNamePos:
      if line[endNamePos + 1] == '(':
        startPathPos = endNamePos + 1
        endPathPos = line.find(')',startPathPos + 1)
        if endPathPos > startPathPos:
          return startNamePos,endNamePos,startPathPos,endPathPos+1
  return 0,0,0,0

def extractImageParts(line):
  startNamePos,endNamePos,startPathPos,endPathPos = imageTag(line)
  imageName = ''
  imagePath = ''
  if endPathPos != 0:
    imageName = 'noName'
    if endNamePos > startNamePos:
      startName = line[startNamePos:endNamePos].rfind('/')
      if startName == -1: startName = line[startNamePos:endNamePos].rfind('\\')
      startName += startNamePos + 1
      imageName = line[startName:endNamePos]
    imagePath = line[startPathPos+1:endPathPos-1]
    startNamePos -= 2
  return line[0:startNamePos], imageName, Path(imagePath), line[endPathPos:] 

def modifyImagePath(imgFile, source_md, imageName):
  # New image path/file-name must have no spaces
  sourceImagePath = Path(pathToURL(source_md).replace('/en/','/media/')).with_suffix('') / imgFile.name
  #sourceImagePath = Path(str(source_md.with_suffix('')).replace('en','media').replace(' ','_')) / imgFile.name
  imageName = Path(pathToURL(imageName)).with_suffix(imgFile.suffix)
  #imageName = Path(imageName.replace(' ','_')).with_suffix(imgFile.suffix)
  newPath = (sourceImagePath.parent / imageName)
  if not (sourceImagePath.parent/imageName).exists():  # Give image sensible name
    sourceImagePath.replace(newPath)
  newPath = str(newPath).replace('\\','/')
  newPath = newPath[newPath.index('/media/'):]
  return newPath

def correctImagePaths(source_md):
  #Aspose path: C:/Hugo/Sites/Life_For_Liberia/static/media/Blog/2018_Ministry_Trip/2018_Ministry_Trip.002.jpeg
  #Writage path: media/2018_Ministry_Trip.002.jpeg
  with source_md.open('r', encoding="utf-8") as original:
    tempFile = source_md.parent / 'tempFile.txt'

    with tempFile.open('w', encoding="utf-8") as temp: 
      sourceImagePath = Path('') 
      for line in original:
        startLine, imageName, imgFile, lineRemainder = extractImageParts(line)
        line = startLine
        while imageName != '' :
          image_Tag = "![" + imageName + "]"
          if imageName == "noName":
            imageName = imgFile.name
          imgFile = modifyImagePath(Path(imgFile), source_md, imageName)
          line += image_Tag + '(' + imgFile + ')'
          startLine, imageName, imgFile, lineRemainder = extractImageParts(lineRemainder)
          line += startLine
        line += lineRemainder

        temp.write(line)

  original.close()
  source_md.unlink()
  temp.close()
  tempFile.replace(source_md)

def imagePathFromSourcePath(source_md: Path, imgRoot):
  pathStr = str(source_md.parent) + '\\'
  pathstart = pathStr.index('\\en\\') + len('\\en\\')
  midPath = pathStr[pathstart:-1]
  imgPath = imgRoot / midPath / source_md.stem
  return Path(pathToURL(imgPath))

def moveImageFiles(source_md, imgRoot):
  sourceImageFolder = source_md.parent / 'media'
  if sourceImageFolder.exists():
    imgFolder =  imagePathFromSourcePath(source_md, imgRoot)
    haveMadeNewFolder(imgFolder)     
    for file in sourceImageFolder.glob('*'):
      imgPath = imgFolder / file.name
      if imgPath.exists():
        file.unlink()
      else: 
        file.replace(imgPath)
    sourceImageFolder.rmdir()
    return True
  return False

# File Conversion
def doc_to_docx(docName):
  print(f"Converting {docName} to .docx")  
  doc = word.Documents.Open(str(docName))
  out_file = docName.with_suffix('.docx')
  doc.SaveAs2(str(out_file), FileFormat=16) # file format for docx
  doc.Close(-1) # save changes
  doc.unlink()

def updateStyles(sourceDoc):
  #word.visible = True
  doc = word.Documents.Open(str(sourceDoc))
  doc.UpdateStylesOnOpen = True
  #print("word_template: " , word_template) 
  doc.AttachedTemplate = word_template
  doc.Fields.Update()
  # find.replace finds but doesn't replace, so do it explicitly!
  findObj = doc.ActiveWindow.Selection.Find
  findObj.ClearFormatting
  findObj.Format = True
  findObj.Style = doc.Styles("Indent")
  #findObj.Replacement.ClearFormatting
  #findObj.Replacement.Style = doc.Styles("Quote")
  findObj.Wrap = 1 # wdFindContinue
  success = success = findObj.Execute(FindText ="") # 2: wdReplaceAll, 1 wdReplaceOne
  while success:
    found = doc.ActiveWindow.Selection.Range
    found.Style = doc.Styles("Quote")
    success = findObj.Execute(FindText ="") # 2: wdReplaceAll, 1 wdReplaceOne

  doc.UpdateStyles()
  doc.Close(SaveChanges=-1) # save changes

def word_to_md(sourcePath, destFile):
  writage_word_saveas_md(sourcePath, destFile)
  #pandoc_WordToMD(sourcePath, file, mediaPath)
  #sub_pandoc_WordToMD(sourcePath, file, mediaPath)
  #mamoth_WordToMD(sourcePath, file)
  #aspose_WordToMD(sourcePath,file, mediaPath)

def writage_word_saveas_md(sourcePath, destFile):
  word.visible = False
  doc = word.Documents.Open(str(sourcePath))
  print(f"Converting {sourcePath.name} to .md")
  doc.SaveAs2(str(destFile), FileFormat=24) # file format for .md
  doc.Close(0) # don't save changes

# def add_heading_bookmarks(doc):
#     for paragraph in doc.Paragraphs:
#         #print("Stlye: " , paragraph.Style.NameLocal)
#         if paragraph.Style.NameLocal == 'Heading 1' or paragraph.Style.NameLocal == 'Heading 2':
#             # Extract the heading text and use it as the bookmark name
#             heading_text = paragraph.Range.Text.strip()
#             bookmark_name = ''.join(filter(str.isalnum, heading_text))
#             print("bookmark_name: " , bookmark_name)
#             paragraph.Range.Bookmarks.Add(bookmark_name)
  
def to_pdf(sourcePath, file, booklet = False):
  try:
    word.visible = False
    doc = word.Documents.Open(str(sourcePath))
    doc.UpdateStylesOnOpen = False   
    doc.PageSetup.TopMargin = '2cm'
    doc.PageSetup.BottomMargin = '2cm'
    doc.PageSetup.LeftMargin = '2cm'
    doc.PageSetup.RightMargin = '2cm'
    doc.AttachedTemplate = word_template  
    #print("Attached after change:", doc.AttachedTemplate.Name)
    doc.UpdateStyles()

    #add_heading_bookmarks(doc)

    if booklet:
      doc.PageSetup.PaperSize = 9 # A5
      #doc.PageSetup.Orientation = 0 
    else:
      doc.PageSetup.PaperSize =7 # A4
      #doc.PageSetup.Orientation = 0 
    
    doc.ExportAsFixedFormat(OutputFileName=str(file), ExportFormat=17, OpenAfterExport=False, OptimizeFor=0, CreateBookmarks=1)

    #doc.SaveAs2(str(file), FileFormat=17, CreateBookmarks=1) # file format for pdf
    doc.Close(0) # don't save changes
  except Exception as err:
    print(err)
  
'''
def mamoth_WordToMD(sourcePath, file):
  # does not render tables
  file = Path(str(file).replace(".","_m.",1))
  result = mammoth.convert_to_markdown(sourcePath)
  with file.open('w', encoding="utf-8") as outFile:
    outFile.write(result.value);
  outFile.close() 

def pandoc_WordToMD(sourcePath, file, mediaPath):
  # Exceptions thrown
  file = Path(str(file).replace(".","_p.",1))
  pypandoc.convert_file(str(sourcePath), 'markdown', extra_args = f"--extract-media={mediaPath}", outputfile=str(file)) 

def sub_pandoc_WordToMD(sourcePath, file, mediaPath):
  # does not render tables
  file = Path(str(file).replace(".","_s.",1))
  parms = ("-s", "-f", "docx", sourcePath,"-t", "markdown", f"--extract-media={mediaPath}", "-o", file)
  subprocess.run([pandocCmd, *parms], shell=False)

def aspose_WordToMD(sourcePath, file, mediaPath):
  # renders tables correctly
  #file = Path(str(file).replace(".","_a.",1))

  doc = aw.Document(str(sourcePath))
  saveOptions = aw.saving.MarkdownSaveOptions()
  saveOptions.images_folder = str(mediaPath)
  doc.save(str(file), saveOptions)
  strip_lines_from_File(file,"Aspose")
  strip_lines_from_File(file,"![](")
  strip_lines_from_File(file,"(#_Toc") # Aspose TOC
'''
# Front-Matter
def get_MultiPage_Summary(allPages):
  '''
  If H3 before first H2, H3 is the summary.
  If no H3 then text before first H1/H2 used as summary.
    For single-page doc, use only first paragraph > 50 chars.
  '''
  h3_summary = -1  
  summary = []
  firstLine = ''

  for lineNo, line in enumerate(allPages[0]):
    if len(line) < 3: continue
    if (line.startswith('# ') or line.startswith('**')): # heading 1, ** Bold for Title style
      if h3_summary >= 0: break
      else: continue
    if h3_summary == -1 and line.startswith('###'): # H3 Summary before first H1 or H2
      h3_summary = lineNo
    #elif line == '###\n': # Text Summary before first H1 or H2
      #pass
    elif (firstLine != '' or h3_summary >= 0) and line.startswith('#'): # any heading terminates summary
      break
    elif h3_summary >= 0:
      summary.append(line.strip())
    elif firstLine == '' and imageTag(line)[2] == 0:
      alphaCount = len(tuple(c for c in line if c.isalpha()))
      if alphaCount > 50:
        firstLine = line
        
  if h3_summary == -1:
    summary = firstLine.strip()
  else:
    #summary = '<br>'.join(summary) 
    summary = '\n\n'.join(summary) 

  summary = convertFromSmartQuotes(summary)
  summary = summary.replace('\\','')
  if len(allPages) > 1:
    del(allPages[0])

  return summary

def cleanFrontMatterString(string):
  string = convertFromSmartQuotes(string)
  string = string.replace('"',"'")
  for char in string:
    if not char.isalnum():
      if char in (':','_'):
        string = string.replace(char,' ')
      elif char in ('*','/','#','|','\\'):
        string = string.replace(char,'')
      elif ord(char) > 127:
        string = string.replace(char,'')
        
  return string

def getDocTitle(page):
  title = None
  h3_summary = False  
  summary = []
 # firstLine = None
  line = None
  #if not '#' in page:
    #return '', ''

  for line in page:

    if len(line) < 3: continue
    elif title is None and ((line.startswith('# ') or line.startswith('**'))): # heading 1, ** Bold for Title style
      title = line[2:].strip()
      title = cleanFrontMatterString(title)
      if h3_summary: break
    elif title is not None and len(summary) == 0 and line.startswith('### '): # Summary from H3 after first H1 and before  H2
      h3_summary = True
    elif h3_summary:
      if line.startswith('#'):
        if title is None: continue
        else: break
      else:
        summary.append(line.strip())
    elif line.startswith('## '): # Create summary from heading 2's
      summary.append(line[2:].strip())
    #elif firstLine is None and imageTag(line)[2] == 0:
      #alphaCount = len(tuple(c for c in line if c.isalpha()))
      #if alphaCount > 50:
        #firstLine = line.strip()
        
  if line is not None and title == None:
    title = '¬' + cleanFrontMatterString(line[:50])
  if len(summary) == 0:
    summary = line[:50]
  else:
    #summary = '<br>'.join(summary) # OK for website, but not pdf's
    summary = '\t\n\n'.join(summary) # need \n\n for pdf's Use \t to identify verse-headings for scripture summary.
  #summary = cleanFrontMatterString(summary)    
  summary = '"' + summary + '"'
  return title, summary

def create_frontMatter (weight, englishTitle, type, title, summary):
  frontMatter = ["---"]
  frontMatter.append("title: " + title)
  frontMatter.append("type: " + type)
  frontMatter.append("translationKey: " + englishTitle)
  frontMatter.append("summary: " + summary)
  frontMatter.append("weight: " + str(weight))
  frontMatter.append("---\n")
  return "\n".join(frontMatter)

# Translation
def nonAlphas(str): # include (.,"?')
  startNon = ''
  endNon = ''
  for c in str:
    if not c.isalpha() and c not in ('"',"'"):
      startNon += c
      str = str[1:]
    else: break

  for c in reversed(str):
    if not c.isalpha() and c not in ('.',',','"',"'",'?'):
      endNon = c + endNon
      str = str[:-1]
    else: break 
  return startNon, str, endNon

def translateBlock(translationBlock, language):
  try:
    startNon, lang_text, endNon = nonAlphas(translationBlock)
    if lang_text != '': lang_text = GoogleTranslator(source='en', target=language).translate(text=lang_text)
    #translated = translator.translate_text(translationBlock, target_lang=language).text
    #translated = translated.text
    if lang_text is None: lang_text = ''
    lang_text = lang_text.replace('\xa0', ' ')
    lang_text = lang_text.replace('] (', '](')    
    lang_text = lang_text.strip()
    lang_text = startNon + lang_text + endNon


  except  Exception as err:
    print(err)
    #raise
  return lang_text

def translateBlockToFile(destFile, translationBlock, language):
  if translationBlock == '\n':
    destFile.write(translationBlock)
  else:
    start = 0
    end = 4000
    while True:
      translated = translateBlock(translationBlock[start:end], language)
      print('.',end='', flush=True)
      destFile.write(translated)
      start = end
      end += 4000
      if start >= len(translationBlock): break
      
  return ""

def repair_TOC(line, startLabel, endLabel, tocEnd):
  label = line[startLabel:endLabel]
  toc = label.replace("'","")
  toc = toc.replace(" ","-")
  toc = toc.lower()
  return line[:startLabel] + label + toc_tag + toc + ')' + line[tocEnd:]

def toc_pos(line, start):
  tocStart = line.find(toc_tag, start)
  if tocStart >= 0:
    labelStart = line.find('[', start) + 1
    tocEnd = line.find(')',tocStart) + 1
    return labelStart, tocStart, tocEnd 
  return 0,0,0

def numeric_heading(line: str): # returns start-pos of an alpha string with digit and next alpha after the digit.
  end_numeric_heading = 0
  start_numeric_heading = 0

  for digitPos, c in enumerate(line,1): # Find position of first digit
    if c.isdigit():       
       break
    elif not c.isalpha():
      start_numeric_heading = digitPos # Find position of first alpha in string containing a digit

  if digitPos < len(line):  # Find position of first alpha after the digit
    for end_numeric_heading, c in enumerate(line[digitPos:],digitPos): # Find position of first digit
      if  c.isalpha():       
         break
  else:
    start_numeric_heading = 0
  return start_numeric_heading, end_numeric_heading

def createMDtranslation(sourceFile, destFile, language):
  # Translate BEFORE inserting front-matter
  tempName = destFile.with_suffix('.temp')
  print(f"Translating {destFile.name} into {language}")
  with sourceFile.open('r', encoding="utf-8") as original:
    with tempName.open('w', encoding="utf-8") as translation: 
      for line in original: # translate one line at a time, to ensure all /n are retained.
        if line == '\n':
          translation.write(line)
          continue

        while len(line) > 0:
          # There may be numeric parts or images to skip
          stopTr,endNamePos,startPathPos,restartTr = imageTag(line)
          gotImage = restartTr != 0
          startNum, endNum = numeric_heading(line)
          gotNumeric = endNum > startNum
          if gotImage and gotNumeric:
            if startNum < stopTr:
              stopTr = startNum
              restartTr = endNum
          elif gotNumeric:
            stopTr = startNum
            restartTr = endNum

          if restartTr > stopTr:
            translateBlockToFile(translation, line[:stopTr], language)  # translate up to start of numeral
            translation.write(line[stopTr:restartTr]) # write numeric
            line = line[restartTr:]
          else: # no image or numeric
            line = translateBlockToFile(translation, line, language)

      translation.close()
      tempName.replace(destFile)
      print()

def loadSourceLanguageHeadings(source_md):
  title = ""
  with source_md.open('r', encoding="utf-8") as originalfile:
    gotTitle = False
    headings = [] # list of Heaadings
    for line in originalfile:
      if len(line) < 5: continue
      if line.startswith('# '): # heading 1
        headings.append(line[2:].replace(':','').strip())
        if not gotTitle:
          title = headings[0]
          gotTitle = True
      elif not gotTitle: # First line for Title style
        title = line.replace('*','').strip()
        gotTitle = True

  if len(headings) == 0 or len(title) > 100:
    title = source_md.stem
    headings.append(title)
      
  return title, headings

def bookOrder(book):
  books = ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1Samuel", "2Samuel", "1Kings", "2Kings", "1Chronicles", "2Chronicles", \
   "Ezra", "Nehemiah", "Esther", "Job", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", \
   "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", \
   "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1Corinthians", "2Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", \
   "1Thessalonians", "2Thessalonians", "1Timothy", "2Timothy", "Titus", "Philemon", "Hebrews", "James", "1Peter", "2Peter", "1John", "2John", "3John", "Jude", "Revelation")
  return books.index(book) if book in books else -1
  

# Top-Level Executed functions

def tableOfScriptures(mdRootPath):
  dictOfScriptures = {}
  print('tableOfScriptures')
  for summary in mdRootPath.rglob('Summary*.md'):
    #print(summary)
    with summary.open('r', encoding="utf-8") as md:
      storyNo = ''
      doc_title = ''
      folder_name = pathToURL(summary.parent.name).lower()
      doc_name = str(summary.name)
      doc_name = pathToURL(doc_name[doc_name.find('_')+1:doc_name.find('.md')]).lower()
      for line in md:
        if line == '\n': continue
        if storyNo == '' and line[:2] != "# ": continue
        if line[:2] == "# ": storyNo = ''
        if storyNo == '':
        
          for end,char in enumerate(line[3:]):
            if not char.isdigit():
              break

          if end == 0 or end == len(line[3:]):
            storyNo = ''
            continue

          storyNo = line[2:3+end]
          doc_title = line[2:-1]
          page_name = pathToURL(doc_title).lower() + '_' + doc_name
        else: # find list of references
          #for ref in line.split('<br>'):
          for ref in line.split('\t\n\n'):
            start = ref.find(':')
            if start == -1:
              start = 0
              while start < len(ref) and not ref[start].isdigit(): start+= 1
              while start < len(ref) and ref[start].isdigit(): start+= 1
              if start == len(ref): start = -1

            if start == -1: continue
            verse = start + 1
            start -= 1
            startVerse_end = 0
            end = 0
            if verse >= 1:
              while verse+end < len(ref) and not ref[verse+end].isalpha(): end+= 1
              while verse+startVerse_end < len(ref) and ref[verse+startVerse_end].isdigit(): startVerse_end+= 1
              while ref[start].isdigit(): start-= 1
              
              chapterNo = '00' + ref[start+1:verse-1]
              chapterNo = chapterNo[-3:]
              verseNo = '00' + ref[verse:verse+startVerse_end]
              verseNo = verseNo[-3:]
              book = ref[:start].replace(' ','')
              bookKey = '0' + str(bookOrder(book))
              bookKey = bookKey[-2:]
              sortKey = bookKey + chapterNo + verseNo
              scripture = ref[:verse+end].strip()

              verseSummary = ref[verse+end:].strip()
              storyLink = '[' + storyNo + '](../' + folder_name + '/' + page_name + ')'
              if sortKey not in dictOfScriptures.keys():
                dictOfScriptures[sortKey] = [scripture, verseSummary, [storyLink]]
              else:
                if verseSummary != '' : dictOfScriptures[sortKey][1] = verseSummary
                if storyLink not in dictOfScriptures[sortKey][2]:
                  dictOfScriptures[sortKey][2].append(storyLink)

  refWidth = 25
  summarWidth = 70
  trainingWidth = 40
  scriptures = ["# Training Scriptures\n\n"]
  scriptures.append("| **Reference** | **Summary** | **Training** |\n")
  scriptures.append(f"|{'-'*refWidth}|{'-'*summarWidth}|{'-'*trainingWidth}|\n")
  for sortKey, entry in sorted(dictOfScriptures.items()):
    #print(sortKey, entry[0], entry[1], entry[2])
    storyNoString = ','.join(entry[2])
    entryStr = '|' + '|'.join([entry[0], entry[1], storyNoString]) + '|\n'
    scriptures.append(entryStr)

  scriptures_md = mdRootPath / 'Training_Scriptures.md'
  pdf_scriptures_file = mdRootPath / 'pdf' / 'Training_Scriptures.pdf'
   
  savePageAs_md(scriptures, scriptures_md)
  to_pdf(scriptures_md, pdf_scriptures_file)        
  header = create_frontMatter(1, "Training Scriptures", 'document', "Training Scriptures", "Training Scriptures")
  prependToPage(scriptures, header)
  savePageAs_md(scriptures, scriptures_md) # re-saved with frontmatter

def updateWebsite(webRootPath):
  ParmsAdd = ("add", ".")
  ParmsCommit = ("commit","-m", "Upload new content")
  ParmsPush = ("push", "origin", "main")
  Git = "git"
  subprocess.run([Git, *ParmsAdd], shell=False, cwd=webRootPath)
  subprocess.run([Git, *ParmsCommit], shell=False, cwd=webRootPath)
  subprocess.run([Git, *ParmsPush], shell=False, cwd=webRootPath)

def main():
  global word_template
  global word
  print('Start...')
  # Prevent Windows from going to sleep
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
  ini_file, webRootPath, sourceRootPath, word_template, sourceLanguage, languages, updated = readINI()
  if updated:
    msg = "Hugo Website root is " + str(webRootPath) + '\n\n'
    msg += "Docx root is " + str(sourceRootPath) + '\n\n'
    msg += "Source Language is: " + sourceLanguage + '\n\n'
    msg += "Template is: " + word_template + '\n\n'
    msg += "Languages are: " + str(languages)
    msg += f"\n\nEdit {ini_file.name} to make changes"
    if Msgbox("docxToHugo_ini.toml", msg, 1) == 2: quit()

  contentRootPath = webRootPath / "content"
  mediaRoot = webRootPath / "static/media"
  source_md_root = webRootPath/'static/en'
  sourceLanguageMDfolder = contentRootPath / sourceLanguage
  re_do_listOfRefs = False


  for sourceDoc in sourceRootPath.rglob('*.doc'):
    if word is None: word = win32com.client.Dispatch("Word.Application")
    if sourceDoc.stem.startswith('~'): continue
    doc_to_docx(sourceDoc)

  deleteRemovedFiles(sourceRootPath, source_md_root, contentRootPath, languages)
  allDocx = sorted(sourceRootPath.rglob('*.docx'))
  sourceRootStart = len(str(sourceRootPath)) + 1
  folder = None
  unableToTranslate = False if do_translations == True else True
  for sourceDoc in allDocx:
    docName = sourceDoc.stem
    if docName.startswith('~'): continue     
    if docName.endswith('_'): continue     
    docFolder = str(sourceDoc.parent)[sourceRootStart:]    
    sourceLanguageMDpath = sourceLanguageMDfolder / docFolder    
    sourceLanguageTitles = []
  
    # convert to basic .md
    #if docName[-2:] == "V3": 
    #if docName[-3:] == "V3_": 
    #if docName == "2017 Ministry Trip": 
    #if docFolder == "Blog":
    #print(docFolder) 
    #if docFolder == r"Teaching\Disciple-Making through Storytelling\New Wineskins": 
    #if sourceLanguageMDpath.name == "Evangelism Stories": 
    if True:
      pass
    else: continue

    if sourceDoc.parent != folder: 
      source_weight = 1
      folder = sourceDoc.parent
    
    source_md = Path(source_md_root/docFolder/sourceDoc.stem).with_suffix('.md')
    if fileNeedsUpdating(sourceDoc, source_md): # update English source.md
      if docFolder.find('01_Apprentice-Training') >= 0: re_do_listOfRefs = True
      deleteAll(source_md,'')
      doc_media = Path(str(source_md.with_suffix('')).replace('\\en\\','\\media\\'))
      deleteAll(doc_media,'')
      for lang in languages:
        mdLangPath = contentRootPath / lang
        deleteAll(mdLangPath / docFolder, sourceDoc.stem)
        
      haveMadeNewFolder(source_md.parent)
      word = win32com.client.Dispatch("Word.Application")
      word.visible = 0  
      updateStyles(sourceDoc)    
      word_to_md(sourceDoc, source_md) # non-website file for pagination and translation, saved in static folder
      if moveImageFiles(source_md, mediaRoot): 
         correctImagePaths(source_md)
            
    makeMultiplePages = source_md.stem.endswith('_m')
    upload_required = False
    for lang in languages: 
      if unableToTranslate and lang != sourceLanguage: continue
      langMDpath = contentRootPath / lang / docFolder       
      pdf_folder = langMDpath /"pdf"
      weight = source_weight
      lang_file = webRootPath/ 'static'/ lang / docFolder / source_md.name
      sourceMD_need_updating = fileNeedsUpdating(source_md, lang_file)
      md_files_need_creating = mdFiles_missing(langMDpath, docName)
      process_doc = sourceMD_need_updating or md_files_need_creating or REDO_PDFS
      if process_doc: # update lang-source.md
        print(f'Update: {lang}/{docName}')
        upload_required = True
        sourceTitle, sourceLanguageTitles = loadSourceLanguageHeadings(source_md)
        # Create content folders               
        createMDfolder(langMDpath, lang, sourceLanguage)       
        haveMadeNewFolder(pdf_folder)
        pdf_A4_file = pdf_folder / (docName + "_A4.pdf") 
        pdf_A5_file = pdf_folder / (docName + "_A5.pdf")     
        if word is None :
          word = win32com.client.Dispatch("Word.Application")
          word.visible = 0  
        # save as combined .pdf        
        if lang == sourceLanguage: 
          if docFolder.find('01_Apprentice-Training') >= 0: re_do_listOfRefs = True
          lang_file = source_md
          langTitle = sourceTitle
          summaryTitle = f"# Summary of {sourceTitle}\n"
          to_pdf(sourceDoc, pdf_A4_file, False)          
          to_pdf(sourceDoc, pdf_A5_file, True)
        else:
          haveMadeNewFolder(lang_file.parent)
          if sourceMD_need_updating: 
            #try:           
              createMDtranslation(source_md, lang_file, lang)
            #except:
              #print("Translation error")
              #unableToTranslate = True
              #continue              
              file_repair_TOC(lang_file)
          langTitle = translateBlock(sourceTitle, lang)
          summaryTitle = translateBlock(f"# Summary of {sourceTitle}\n", lang)

          to_pdf(lang_file, pdf_A4_file, booklet = False)          
          to_pdf(lang_file, pdf_A5_file, booklet = True)

        pages = [0]         
        # split into list of one or more h1 files
        pages = combinedMD_to_pages(lang_file) # page[0] may be the multi-page summary
        #if lang != sourceLanguage: lang_file.unlink()
        summaries = []
        directorySummary = get_MultiPage_Summary(pages) # deletes summary page[0] if found
        if len(directorySummary) > 0:
          summaries.append(directorySummary)
          addSummaryTo_index(langMDpath, directorySummary)

        for pageNo, page in enumerate(pages):
          if len(page) == 0: continue
          title, summary = getDocTitle(page)
          if title == '': continue
          if makeMultiplePages:
            pageTitle = '\n# ' + title + '\n\n'
            print(f'Page: {title}')
            summaries.append(pageTitle + summary.replace('"',''))            
            if title[0] == '¬':
              msg = f'First line of "{docName}" is not Bold or Heading 1. It is\n'
              msg += f'"{title[1:]}"\n Do you want to use {docName}?'
              if Msgbox(docFolder, msg, 1) == 2: continue
              title = docName.replace("_"," ")
          elif len(summaries) > pageNo and summaries[pageNo] != '':
            summary = summaries[pageNo]
            summary = summary.replace('"',"'")
            summary = '"' + summary + '"'
            summary = summary.replace("#","")
            summary = summary.replace("*","")

          md_filename = langMDpath / f'{docName}.md'

          if makeMultiplePages:
            title_path = title.replace('/',' ').replace('?',' ').strip()
            md_filename = langMDpath / f'{title_path}_{docName}.md'
            pdf_page_file = pdf_folder / f'{title_path}_{docName}_A4.pdf'
            pdf_page = page[:]
            pdf_page.insert(0,f'# {langTitle}\n')
            savePageAs_md(pdf_page, md_filename)
            to_pdf(md_filename, pdf_page_file, booklet = False)

          #if lang == sourceLanguage: sourceLanguageTitles.append(title)
          header = create_frontMatter(weight + pageNo + 1, sourceLanguageTitles[pageNo], 'document', title, summary)  
          prependToPage(page, header)
          savePageAs_md(page, md_filename) # re-saved with frontmatter
        # next page

        if makeMultiplePages:
          a4Name = pdf_A4_file.with_stem(pdf_A4_file.stem + '_')
          a5Name = pdf_A5_file.with_stem(pdf_A5_file.stem + '_')
          if a4Name.exists() : a4Name.unlink()
          if a5Name.exists() : a5Name.unlink()
          if pdf_A4_file.exists() : pdf_A4_file.replace(a4Name)
          if pdf_A5_file.exists() : pdf_A5_file.replace(a5Name)
  
          pdf_Summary_file = pdf_folder / f'Summary_{docName}_A5.pdf'
          summaries.insert(0,summaryTitle)
          summaries_md = langMDpath / f'Summary_{docName}.md'
          savePageAs_md(summaries, summaries_md)
          to_pdf(summaries_md, pdf_Summary_file, booklet = True)        
          header = create_frontMatter(weight, sourceTitle + " Summary", 'document', summaryTitle[2:], summaryTitle[2:])
          prependToPage(summaries, header)
          savePageAs_md(summaries, summaries_md) # re-saved with frontmatter

        weight += len(pages); 
        # end updated
      else:
        fileSearch = f'*{docName}.md'
        matched = tuple(sourceLanguageMDpath.glob(fileSearch))
        weight += len(matched);
      # end if needs updating
    # next language              
    source_weight = weight
    if upload_required:updateWebsite(webRootPath)
    
  # next SourceDoc
  re_do_listOfRefs = True
  if re_do_listOfRefs: tableOfScriptures(webRootPath / "content/en/01_Apprentice-Training")
  updateWebsite(webRootPath)
  # Allow Windows to go to sleep again (optional)
  ctypes.windll.kernel32.SetThreadExecutionState(0x00000000)  # ES_CONTINUOUS
  if word is not None: word.Quit()

main()
