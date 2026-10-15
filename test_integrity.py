with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

required_ids = [
    'directPostUrls', 'directUrlsCountBadge', 'directScrapeComments',
    'directCommentsLimitContainer', 'directMaxComments', 'directLimitValue',
    'btnDirectScrape', 'directTerminalContainer', 'directTerminalLogs',
    'directScrapeStatusText', 'wordCloudStudioModal', 'tabStudioWordsBtn',
    'tabStudioShapeBtn', 'tabStudioTypeBtn', 'tabStudioColorsBtn',
    'tabStudioWords', 'tabStudioShape', 'tabStudioType', 'tabStudioColors',
    'studioWordsCountLabel', 'newStudioWordInput', 'newStudioWordWeight',
    'studioWordsTableBody', 'studioFontFamily', 'studioPaddingVal',
    'studioPaddingRange', 'studioMaxWordsVal', 'studioMaxWordsRange',
    'studioPreviewShapeBadge', 'studioPlacedWordsBadge', 'studioPreviewCanvas'
]

missing = [i for i in required_ids if f'id="{i}"' not in html]
print('Missing DOM IDs:', len(missing), missing)
