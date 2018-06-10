#!/bin/env python
# -*- coding:utf-8 -*-

import sys
import os
import re
import codecs

############################  中文排序相关  ###########################
# 建立拼音辞典
dic_py = {}
def loadPinYinInfo():
    f_py = open('py.txt',"r")
    content_py = f_py.read()
    lines_py = content_py.split('\n')
    n=len(lines_py)
    for i in range(0,n-1):
        word_py, mean_py = lines_py[i].split('\t', 1)#将line用\t进行分割，最多分一次变成两块，保存到word和mean中去
        dic_py[word_py]=mean_py
    f_py.close()

# 建立笔画辞典
dic_bh = {}
def loadBhInfo():
    f_bh = open('bh.txt',"r")
    content_bh = f_bh.read()
    lines_bh = content_bh.split('\n')
    n=len(lines_bh)
    for i in range(0,n-1):
        word_bh, mean_bh = lines_bh[i].split('\t', 1)#将line用\t进行分割，最多分一次变成两块，保存到word和mean中去
        dic_bh[word_bh]=mean_bh
    f_bh.close()


# 辞典查找函数
def searchdict(dic,uchar):
    if isinstance(uchar, str):
        uchar = unicode(uchar,'utf-8')
    if uchar >= u'\u4e00' and uchar<=u'\u9fa5':
        value=dic.get(uchar.encode('utf-8'))
        if value == None:
            value = '*'
    else:
        value = uchar
    return value
    
#比较单个字符
def comp_char_PY(A,B):
    if A==B:
        return -1
    pyA=searchdict(dic_py,A)
    pyB=searchdict(dic_py,B)
    if pyA > pyB:
        return 1
    elif pyA < pyB:
        return 0
    else:
        bhA=eval(searchdict(dic_bh,A))
        bhB=eval(searchdict(dic_bh,B))
        if bhA > bhB:
            return 1
        elif bhA < bhB:
            return 0
        else:
            return "Are you kidding?"

#比较字符串
def comp_char(A,B):
    charA = A.decode("utf-8")
    charB = B.decode("utf-8")
    n=min(len(charA),len(charB))
    i=0
    while i < n:
        dd=comp_char_PY(charA[i],charB[i])
        if dd == -1:
            i=i+1
            if i==n:
                dd=len(charA)>len(charB)
        else:
            break
    return dd

# 排序函数
def cnsort(nline):
    n = len(nline)
    for i in range(1, n):  # 插入法
        tmp = nline[i]
        j = i
        while j > 0 and comp_char(nline[j-1],tmp):
            nline[j] = nline[j-1]
            j -= 1
        nline[j] = tmp
    return nline

############################  主流程  ###########################

#python的str默认是ascii编码,设为utf8
reload(sys)
sys.setdefaultencoding('utf8')
#xib和storyboard本质是用XML表示的，有几个特殊符号会被转化成其他字符，所以搜索的时候要做替换
#详情:http://xml.silmaril.ie/specials.html
XML_File_Format = [".storyboard", ".xib"]
XML_Special_Character_Map = {'<':'&lt;', '&':'&amp;', '>':'&gt;', '\"':'&quot;', '\'':'&apos;'}
#只搜索这些文件里面的字符串
Const_File_Format = [".h", ".m", ".mm", ".storyboard", ".xib", ".swift"]
#这些文件夹不搜索
Const_Dont_Search_Dir_Suffix = ["\.xcodeproj", "\.xcworkspace", "\.git", "Pods", "fastlane", "AutoBuild", "\.framework", "\.bundle", "\.a", "findUnusedResource"]
#当前工程路径
currentDirPath = os.path.dirname(os.path.realpath(__file__))
#所有本地字符串数组
allLocaizedStrings = []
#没有用到的字符串数组
unusedLocalizedStrings = []
#是否只搜索被xcode引用的文件
onlySearchInProject = None
pbxprojPath = None
unReferredFileNameCache = {}
#处理用户输入
y = 1
n = 0

#加载所有本地字符串
def loadAllLocaizedStrings(file_path):
    try:
        f = codecs.open(file_path, 'r+', encoding='utf16')
        allLines = f.readlines()
        regexString = '[ ]*\".+\"[ ]*=[ ]*\".+\"[ ]*;[ ]*'
        regex = re.compile(regexString)
        for line in allLines:
            match = regex.search(line)
            if match:
                stringArr = line.split('=')
                length = len(stringArr)
                if length == 2:
                    utf16String = stringArr[0].strip()
                    utf8String = utf16String.encode('utf8')
                    allLocaizedStrings.append(utf8String)
                elif length > 2:
                    #如果数组的长度大于2，说明字符串本身包含了等于号，特殊处理
                    utf8Line = line.encode('utf8')
                    index = utf8Line.find('\" = \"')
                    subString = utf8Line[0:index+1]
                    allLocaizedStrings.append(subString)
        f.close()
    except Exception,e:
        print(e)

#遍历所有本地字符串，搜索所有文件，并把没有用到的字符串写到/unusedLocalizedStrings.log里面去
def findLocalizedString():
    #获取工程路径,当前路径去掉最后一部分就行
    dirPathComponents = currentDirPath.split('/')
    del dirPathComponents[len(dirPathComponents) - 1]
    projectPath = '/'.join(dirPathComponents)

    logPath = currentDirPath + '/unusedLocalizedStrings.log'
    length = len(allLocaizedStrings)
    wf = None
    if length > 0:
        print("一共需要搜索 %d 个本地字符串" % length)
        for localizedString in allLocaizedStrings:
            print("正在搜索:" + localizedString)
            #在XML把特殊字符替换掉
            XMLLocalizedString = replaceXMLSpecialCharacterInString(localizedString)
            bfind = traversalDirRecursively(projectPath ,localizedString, XMLLocalizedString)
            if bfind == 0:
                # print(localizedString + '没有被用到')
                unusedLocalizedStrings.append(localizedString)
                if wf == None:
                    try:
                        bExists = os.path.exists(logPath)
                        if not bExists:
                            wf = open(logPath, 'w')
                        else:
                            wf = open(logPath, 'r+')
                            wf.seek(0)
                            wf.truncate()
                    except Exception,e:
                        print e
                wf.write(localizedString + '\n')
        if wf != None:
            wf.close()
            print('共找到 %d 个没用到的本地字符串' % len(unusedLocalizedStrings))
            print('您可以在 ' + logPath + ' 查看所有没用到的字符串.')
            choice = input('是否需要删除本地化文件中没用到的字符串?(y or n):\n')
            if choice == 1:
                #加载中文排序所需要的信息
                print('正在加载中文排序所需要的信息...')
                loadPinYinInfo()
                loadBhInfo()
                print('开始删除本地字符串文件中没用到的字符串...')
                deleteUnusedLocalizedStringsInFiles()
                print('如果需要删除更多文件中的无用字符串，请在最初调用的时候带上后续的路径参数，用空格隔开就行.')
            choice = input('是否需要删除无用字符串的文件?(y or n):\n')
            if choice == 1:
                exists = os.path.exists(logPath)
                if not exists:
                    print('文件不存在，已经被删除.')
                else:
                    os.remove(logPath)
                    print('文件已删除.')
        
#自动删除本地字符串文件中没有用到的字符串
def deleteUnusedLocalizedStringsInFiles():
    #一个一个文件删除
    right = len(sys.argv)
    if onlySearchInProject == 1:
        right = right - 1
    for index in range(1, right):
        tempArr = []
        for unusedLocalizedString in unusedLocalizedStrings:
            tempArr.append(unusedLocalizedString)
        path = sys.argv[index]
        try:
            f = codecs.open(path, 'r+', encoding='utf16')
            arragedAllLines = arrageAllLines(f.readlines())
            f.seek(0)
            f.truncate()
            for line in arragedAllLines:
                length = len(tempArr)
                utf8Line = line.encode('utf8')
                bFind = 0
                for i in range(length):
                    string = tempArr[i]
                    if string in utf8Line:
                        bFind = 1
                        del tempArr[i]
                        break
                if bFind == 0:
                    f.write(line)
            f.close()
            print(path + ' 删除完毕.')
        except Exception,e:
            print(e)

#整理文件：去重，排序，删除注释，删除空行
def arrageAllLines(allLines):
    #去重
    tempDic = {}
    for line in allLines:
        tempDic[line] = '1'
    
    allLinesAfterDuplicateRemoval = tempDic.keys()
    unsortedAllLines = []
    for line in allLinesAfterDuplicateRemoval:
        #去除空行
        if len(line) == 0:
            continue
        #去除注释
        if line.startswith('//'):
            continue
        if line.startswith('/*'):
            continue
        unsortedAllLines.append(line)
    #如果需要按中文排序，注释掉255行，打开256行就行
    return unsortedAllLines
    # return cnsort(unsortedAllLines)

#递归遍历所有文件，搜索对应的本地字符串
def traversalDirRecursively(dirPath, localizedString, XMLLocalizedString):
    #不搜索的文件夹直接return 0
    dirPathComponents = dirPath.split('/')
    dirLastPathComponent = dirPathComponents[len(dirPathComponents) - 1]
    for pathSuffix in Const_Dont_Search_Dir_Suffix:
        regexString = '.*' + pathSuffix + '$'
        regex = re.compile(regexString)
        match = regex.search(dirLastPathComponent)
        if match:
            return 0
    #遍历当前文件夹 
    bfind = 0
    for fileName in os.listdir(dirPath):
        filePath = os.path.join(dirPath, fileName)
        if (os.path.isfile(filePath)):
            fileFormat = os.path.splitext(fileName)[1]
            if (fileFormat in Const_File_Format):
                shouldContinue = 1
                if onlySearchInProject == 1:
                    value = unReferredFileNameCache.get(fileName)
                    if value == None:
                        shouldContinue = checkFileIfReferredByProject(fileName)
                        unReferredFileNameCache[fileName] = shouldContinue
                    else:
                        shouldContinue = value
                if shouldContinue == 1:
                    if (fileFormat in XML_File_Format):
                        bfind = findStringInFile(filePath, XMLLocalizedString)
                    else:
                        bfind = findStringInFile(filePath, localizedString)
                    if bfind == 1:
                        return 1
        else:
            bfind = traversalDirRecursively(filePath, localizedString, XMLLocalizedString)
            if bfind == 1:
                return 1
    return bfind

#遍历单个文件所有文字，查找是否包含对应的本地字符串
def findStringInFile(file_path, subString):
    try:
        f = open(file_path,'r+')
        allLines = f.readlines()
        l_bfind = 0
        for line in allLines:
            if subString in line:
                l_bfind = 1
                break
        f.close()
        return l_bfind
    except Exception,e:
        print(e)
        return 0

#查看文件是否被工程引用
def checkFileIfReferredByProject(fileName):
    return findStringInFile(pbxprojPath, fileName)

#把字符串在XML格式中的特殊字符替换掉
def replaceXMLSpecialCharacterInString(oriString):
    if len(oriString) <= 2:
        return oriString
    characters = []
    for s in oriString:  
        characters.append(s)
    #跳过两端的双引号
    for index in range(1,len(characters) - 1):
        c = characters[index]
        if (c in XML_Special_Character_Map.keys()):
            characters[index] = XML_Special_Character_Map[c]
    return ''.join(characters)

def onlyArrageStringsFile():
    loadPinYinInfo()
    loadBhInfo()
    for index in range(1, len(sys.argv) - 1):
        path = sys.argv[index]
        print('开始整理:' + path)
        try:
            f = codecs.open(path, 'r+', encoding='utf16')
            arragedAllLines = arrageAllLines(f.readlines())
            f.seek(0)
            f.truncate()
            for line in arragedAllLines:
                f.write(line)
            f.close()
            print('整理完毕.')
        except Exception,e:
            print(e)

#主函数入口
def main():
    global onlySearchInProject, pbxprojPath
    argCount = len(sys.argv)
    if (argCount < 2):
        print('缺少本地字符串路径参数')
    else:
        lastArg = sys.argv[argCount - 1]
        if lastArg == '-arrage':
            if argCount < 3:
                print('缺少本地字符串路径参数')
            else:
                #只整理和排序
                onlyArrageStringsFile()
        else:
            if lastArg == '-onlyInProject':
                onlySearchInProject = 1
                pbxprojPath = sys.argv[argCount - 2]
            locaizedStringsFilePath = sys.argv[1]
            loadAllLocaizedStrings(locaizedStringsFilePath)
            findLocalizedString()

main()
