#!/bin/env python
# -*- coding:utf-8 -*-

import sys
import os
import re

#python的str默认是ascii编码,设为utf8
reload(sys)
sys.setdefaultencoding('utf8')
#当前路径
currentDirPath = os.path.dirname(os.path.realpath(__file__))
#获取工程路径,当前路径去掉最后一部分就行
def getCurrentProjectPath():
    dirPathComponents = currentDirPath.split('/')
    del dirPathComponents[len(dirPathComponents) - 1]
    return '/'.join(dirPathComponents)
#当前工程路径
projectPath = getCurrentProjectPath()
pbxprojPath = ''
#日志路径
preliminaryLogPath = currentDirPath + '/preliminaryUnusedImages.txt'
finalLogPath = currentDirPath + '/finalUnusedImages.txt'
#图片文件格式
Const_Image_File_Format = ['.png', '.jpg']
#图片可能带有的后缀
Const_Image_Name_Suffix = ['@2x', '@3x']
#xib,storyboard和plist本质是用XML表示的，有几个特殊符号会被转化成其他字符，所以搜索的时候要做替换
#详情:http://xml.silmaril.ie/specials.html
XML_File_Format = [".storyboard", ".xib", ".plist"]
XML_Special_Character_Map = {'<':'&lt;', '&':'&amp;', '>':'&gt;', '\"':'&quot;', '\'':'&apos;'}
#只搜索这些文件里面的字符串
Const_File_Format = [".h", ".m", ".mm", ".storyboard", ".xib", ".swift", ".plist", ".json"]
#这些文件夹不搜索, Images.xcassets比较特殊，图片写在json里面，可能还有写在plist里面的，这些都比较特殊，为了加快搜索速度，这里简单排除一下
Const_Dont_Search_Dir_Suffix = ["\.xcodeproj", "\.xcworkspace", "\.git", "Pods", "fastlane", "\.framework", "\.bundle", "\.a"]
#图片白名单：针对工程里面某些特殊的写法匹配不到，增加白名单机制，优先过滤掉
ImageNameWhiteList = []
#存储图片名字字典 key:imageName value:imagePath
allImagesDic = {}
#因为把图片后面的2x 3x去掉，会导致key相同，可能会导致路径丢失，所以图片名字单独存
allImageNames = []
#存储所有没用到的图片名字
allUnusedImageNames = []
#处理用户选项
y = 1
n = 0

#正常搜索流程
def normalSearch():
    loadAllImageNameRecursively(projectPath)
    filterSameNameImages()
    findImageNames()

#加载所有图片名字
def loadAllImageNameRecursively(dirPath):
    shouldContinue = shouldContinueSearchingInDir(dirPath)
    if shouldContinue:
        for fileName in os.listdir(dirPath):
            filePath = os.path.join(dirPath, fileName)
            if (os.path.isfile(filePath)):
                fileInfo = os.path.splitext(fileName)
                if len(fileInfo) == 2:
                    fileFormat = fileInfo[1]
                    if (fileFormat in Const_Image_File_Format):
                        allImagesDic[fileName] = filePath
            else:
                loadAllImageNameRecursively(filePath)

#图片名字去重
def filterSameNameImages():
    tempDic = {}
    for key in allImagesDic.keys():
        imageName = getImageNameFromOriImageName(key)
        tempDic[imageName] = '1'
    for key in tempDic.keys():
        allImageNames.append(key)

#把白名单里面的图片名字去掉
def filterImageNameInWhiteList(imageNames):
    if len(ImageNameWhiteList) > 0:
        print('当前白名单正则如下:')
        for regexString in ImageNameWhiteList:
            print(regexString)
        choice = input('如果有不对可以修改，是否需要过滤?(y or n):\n')
        if choice == 1:
            imageNamesAfterFilter = []
            regexes = []
            for regexString in ImageNameWhiteList:
                regex = re.compile(regexString)
                regexes.append(regex)
            for imageName in imageNames:
                match = False
                for regex in regexes:
                    if regex.search(imageName):
                        match = True
                        break
                if match == False:
                    imageNamesAfterFilter.append(imageName)
                else:
                    print(imageName + ' 被过滤')
            print('过滤完成！')
            return imageNamesAfterFilter
        else:
            return imageNames
    else:
        return imageNames

#查找所有没用到的图片名字
def findImageNames():
    global allImageNames
    allImageNames = filterImageNameInWhiteList(allImageNames)
    length = len(allImageNames)
    if length > 0:
        print("一共需要搜索 %d 个图片名字" % length)
        sortedImageNames = sorted(allImageNames)
        for index in range(len(sortedImageNames)):
            imageName = sortedImageNames[index]
            print("正在搜索第%d个:" % index + imageName)
            XMLImageName = replaceXMLSpecialCharacterInString(imageName)
            bfind = traversalDirRecursively(projectPath ,imageName, XMLImageName, 0)
            if bfind == 0:
                allUnusedImageNames.append(imageName)
        preliminarySearchHasDone()
    else:
        print('没有找到图片资源，本次任务结束')

#递归遍历所有文件，搜索对应的图片名字,searchMode:0-普通搜索,1-模糊搜索
def traversalDirRecursively(dirPath, stringOrRegex, XMLStringOrRegex, searchMode):
    shouldContinue = shouldContinueSearchingInDir(dirPath)
    if shouldContinue:
        #遍历当前文件夹
        bfind = 0
        for fileName in os.listdir(dirPath):
            filePath = os.path.join(dirPath, fileName)
            if (os.path.isfile(filePath)):
                fileFormat = os.path.splitext(fileName)[1]
                if (fileFormat in Const_File_Format):
                    if (fileFormat in XML_File_Format):
                        bfind = findImageNameInFile(filePath, XMLStringOrRegex, searchMode)
                    else:
                        bfind = findImageNameInFile(filePath, stringOrRegex, searchMode)
                    if bfind == 1:
                        return 1
            else:
                bfind = traversalDirRecursively(filePath, stringOrRegex, XMLStringOrRegex, searchMode)
                if bfind == 1:
                    return 1
        return bfind
    else:
        return 0

#遍历单个文件所有文字，查找是否包含对应的图片名字
def findImageNameInFile(file_path, stringOrRegex, searchMode):
    try:
        f = open(file_path,'r')
        allLines = f.readlines()
        l_bfind = 0
        for line in allLines:
            if searchMode == 0:
                if stringOrRegex in line:
                    l_bfind = 1
                    break
            else:
                if stringOrRegex.search(line):
                    l_bfind = 1
                    break
        f.close()
        return l_bfind
    except Exception,e:
        print(e)
        return 0

#初步搜索（拿图片名字去匹配）完成
def preliminarySearchHasDone():
    if len(allUnusedImageNames) > 0:
        print('初步找到 %d 个没用到的图片' % len(allUnusedImageNames))
        succ = writeUnusedNamesToFile(allUnusedImageNames, preliminaryLogPath)
        if succ:
            print('您可以在 ' + preliminaryLogPath + ' 查看初步搜索后没用到的图片的名字.')
            unusedImageNames = readAllLinesFromFile(preliminaryLogPath)
            if len(unusedImageNames) > 0:
                print('您可以修改这个文件，把确定用到的图片名字从文件里删除.')
                choice0 = input('是否对剩下的图片名字做模糊搜索?(y or n):\n')
                if choice0 == 1:
                    startBlurSearch(unusedImageNames, True)
                else:
                    choice1 = input('是否需要自动删除没用到的图片？(y or n):\n')
                    if choice1 == 1:
                        autoDeleteUnusedImage(unusedImageNames, pbxprojPath)
                    choice2 = input('是否需要删除自动生成的字符串文件？(y or n):\n')
                    if choice2 == 1:
                        deleteFile(preliminaryLogPath)
                    print('本次任务结束.')
            else:
                print('没有无用图片可删除，本次任务结束.')
        else:
            print('写入文件失败，本次任务结束')
    else:
        print('没有搜索到无用图片，本次任务结束')

#开始模糊搜索
def startBlurSearch(unusedImageNames, needDeletePreliminaryLog):
    length = len(unusedImageNames)
    if length > 0:
        unusedImagesAfterBlurSearch = _startBlurSearch(unusedImageNames)
        if len(unusedImagesAfterBlurSearch) > 0:
            print('模糊搜索找到 %d 个没用到的图片' % len(unusedImagesAfterBlurSearch))
            succ1 = writeUnusedNamesToFile(unusedImagesAfterBlurSearch, finalLogPath)
            if succ1:
                print('您可以在 ' + finalLogPath + ' 查看模糊搜索后没用到的图片的名字.')
                print('您可以修改这个文件，把确定用到的图片名字从文件里删除.')
                finalUnusedImageNames = readAllLinesFromFile(finalLogPath)
                if len(finalUnusedImageNames) > 0:
                    choice4 = input('是否需要自动删除没用到的图片？(y or n):\n')
                    if choice4 == 1:
                        autoDeleteUnusedImage(finalUnusedImageNames, pbxprojPath)
                else:
                    print('没有无用图片可删除')
                choice5 = input('是否需要删除自动生成的字符串文件？(y or n):\n')
                if choice5 == 1:
                    if needDeletePreliminaryLog:
                        deleteFile(preliminaryLogPath)
                    deleteFile(finalLogPath)
                print('本次任务结束.')
            else:
                print('写入文件失败，本次任务结束')
        else:
            print('没有搜索到无用图片')
            if needDeletePreliminaryLog:
                choice3 = input('是否需要删除自动生成的字符串文件？(y or n):\n')
                if choice3 == 1:
                    deleteFile(preliminaryLogPath)
            print('本次任务结束')
    else:
        print('没有无用图片可搜索，本次任务结束')

def _startBlurSearch(unusedImageNames):
    length = len(unusedImageNames)
    print("还需要搜索 %d 个图片名字" % length)
    tempArr = []
    for index in range(len(unusedImageNames)):
        imageName = unusedImageNames[index]
        print("正在搜索第%d个:" % index + imageName)

        blurSearhRegexString = getBlurSearchImageNameFromOriImageName(imageName)
        regexString = '.*' + blurSearhRegexString + '.*'
        regex = re.compile(regexString)

        XMLImageName = replaceXMLSpecialCharacterInString(imageName)
        XMLBlurSearhRegexString = getBlurSearchImageNameFromOriImageName(XMLImageName)
        XMLRegexString = '.*' + XMLBlurSearhRegexString + '.*'
        XMLRegex = re.compile(XMLRegexString)

        bfind = traversalDirRecursively(projectPath, regex, XMLRegex, 1)
        if bfind == 0:
            tempArr.append(imageName)
    return tempArr

#自动删除工程中的图片资源
def autoDeleteUnusedImage(unusedImageNames, pbxprojPath):
    length0 = len(allImagesDic.keys())
    length1 = len(unusedImageNames)
    length2 = len(pbxprojPath)
    if length0 == 0:
        print("工程图片文件加载不成功或者没有图片, 本次任务结束")
    if length1 == 0:
        print('没有需要删除的图片, 本次任务结束')
        return
    if length2 == 0:
        print('project.pbxproj 路径不存在, 本次任务结束')
        return
    
    try:
        #先准备好所有要删除的图片路径和对应的名字
        tempDic = {}
        for unusedImageName in unusedImageNames:
            oriImageNames = getOriImageNamesFromImageName(unusedImageName)
            if len(oriImageNames) == 0:
                continue
            else:
                for imageName in oriImageNames:
                    tempDic[imageName] = allImagesDic[imageName]
        
        print('一共需要删除%d张图片' % len(tempDic.keys()))
        wf = open(pbxprojPath, 'r+')
        pbxprojLines = wf.readlines()
        wf.seek(0)
        wf.truncate()
        print('开始删除工程文件里面的图片信息...')
        for line in pbxprojLines:
            bFound = 0
            for key in tempDic.keys():
                if key in line:
                    bFound = 1
                    break
            if bFound == 0:
                wf.write(line)
            # else:
            #     print(line + '已删除')
        wf.close()
        print('开始删除图片文件...')
        for value in tempDic.values():
            deleteFile(value, False)
        print('删除完成，本次任务结束')
    except Exception,e:
        print e
        print('本次任务结束')


#把没用到的图片名字写入文件
def writeUnusedNamesToFile(unusedImageNames, filePath):
    wf = None
    try:
        bExists = os.path.exists(filePath)
        if not bExists:
            wf = open(filePath, 'w')
        else:
            wf = open(filePath, 'r+')
            wf.seek(0)
            wf.truncate()
        for imageName in unusedImageNames:
            wf.write(imageName + '\n')
        wf.close()
        return True
    except Exception,e:
        print e
        return False

#从文件读取信息
def readAllLinesFromFile(filePath):
    try:
        bExists = os.path.exists(filePath)
        if not bExists:
            print(filePath + ' 文件不存在.')
            return []
        else:
            rf = open(filePath, 'r')
            tempLines = rf.readlines()
            rf.close()
            allLines = []
            for line in tempLines:
                length = len(line)
                s1 = line[0:length-1]
                s2 = s1.rstrip()
                allLines.append(s2)
            return allLines
    except Exception,e:
        print e
        return []

#根据路径删除文件
def deleteFile(filePath, shouldPrintLog=True):
    exists = os.path.exists(filePath)
    if not exists:
        if shouldPrintLog:
            print(filePath + ' 文件不存在')
    else:
        os.remove(filePath)
        if shouldPrintLog:
            print(filePath + ' 文件已删除.')

#从原始图片名字里面获取待搜索的图片名字，删除掉@2x或@3x的后缀
def getImageNameFromOriImageName(oriImageName):
    fileInfo = oriImageName.split('.')
    imageName = fileInfo[0]
    for suffix in Const_Image_Name_Suffix:
        index = imageName.find(suffix)
        if index >= 0:
            return imageName[0:index]
    return imageName

#从图片名字获取原始图片名字
def getOriImageNamesFromImageName(imageName):
    oriImageNames = []

    attempt0 = imageName + '.png'
    if allImagesDic.get(attempt0) != None:
        oriImageNames.append(attempt0)
    
    attempt1 = imageName + '@2x.png'
    if allImagesDic.get(attempt1) != None:
        oriImageNames.append(attempt1)

    attempt2 = imageName + '@3x.png'
    if allImagesDic.get(attempt2) != None:
        oriImageNames.append(attempt2)

    attempt3 = imageName + '.jpg'
    if allImagesDic.get(attempt3) != None:
        oriImageNames.append(attempt3)

    return oriImageNames

#把数字用正则替换，做模糊搜索
def getBlurSearchImageNameFromOriImageName(oriImageName):
    allNumRegexString = '^[0-9][0-9]+[0-9]$'
    regex = re.compile(allNumRegexString)
    if regex.search(oriImageName):
        #如果是纯数字的直接返回，这种一般都是特殊的图片
        return oriImageName
    characters = []
    jumpTag = 0
    for s in oriImageName:
        if s in '1234567890':
            if jumpTag == 0:
                characters.append('((\d+)|(%d))')
                jumpTag = 1
        else:
            characters.append(s)
            jumpTag = 0
    return ''.join(characters)

#根据dirPath判断是否需要在这个文件夹搜索
def shouldContinueSearchingInDir(dirPath):
    dirPathComponents = dirPath.split('/')
    dirLastPathComponent = dirPathComponents[len(dirPathComponents) - 1]
    for pathSuffix in Const_Dont_Search_Dir_Suffix:
        regexString = '.*' + pathSuffix + '$'
        regex = re.compile(regexString)
        match = regex.search(dirLastPathComponent)
        if match:
            return False
    return True

#把字符串在XML格式中的特殊字符替换掉
def replaceXMLSpecialCharacterInString(oriString):
    characters = []
    for s in oriString:  
        characters.append(s)
    for index in range(len(characters)):
        c = characters[index]
        if (c in XML_Special_Character_Map.keys()):
            characters[index] = XML_Special_Character_Map[c]
    return ''.join(characters)

#主函数入口
def main():
    global pbxprojPath
    argCount = len(sys.argv)
    if argCount > 1:
        arg1 = sys.argv[1]
        if arg1 == '-blurSearch':
            #根据文件路径做模糊搜索
            if argCount > 2:
                filePath = sys.argv[2]
                if argCount > 3:
                    loadAllImageNameRecursively(projectPath)
                    pbxprojPath = sys.argv[3]
                imageNamesForSearch = readAllLinesFromFile(filePath)
                imageNamesForSearch = filterImageNameInWhiteList(imageNamesForSearch)
                startBlurSearch(imageNamesForSearch, False)
            else:
                print('缺少待模糊搜索的路径参数')
        elif arg1 == '-autoDelete':
            #根据文件路径自动删除工程中的图片资源
            if argCount > 3:
                loadAllImageNameRecursively(projectPath)
                filePath = sys.argv[2]
                pbxprojPath = sys.argv[3]
                imageNamesForDelete = readAllLinesFromFile(filePath)
                imageNamesForDelete = filterImageNameInWhiteList(imageNamesForDelete)
                autoDeleteUnusedImage(imageNamesForDelete, pbxprojPath)
            else:
                print('缺少自动删除的路径参数或者project.pbxproj路径参数')
        else:
            pbxprojPath = sys.argv[1]
            normalSearch()
    else:
        normalSearch()
main()
