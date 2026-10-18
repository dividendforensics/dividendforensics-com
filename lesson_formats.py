"""Topic-led reading layouts; preserve the reviewed prose, figures and sources."""
from bs4 import BeautifulSoup

LABELS = {
    'concept': ('Concept essay', 'Start with the idea.'),
    'sector': ('Business field notes', 'Follow the business model.'),
    'calculation': ('Calculation notebook', 'Read the definition. Then work the numbers.'),
    'risk': ('Risk briefing', 'Separate the risk from the headline.'),
    'workflow': ('Reading workflow', 'Turn a filing into an evidence trail.'),
    'workshop': ('Research workshop', 'Work the case. Challenge the conclusion.'),
}

# Display-only summaries of the existing hypothetical examples, not live data.
NUMBER_NOTES = {
    'learn-ffo': ('USD millions · simplified bridge', [('Net income', '40'), ('Depreciation adjustment', '+ 50'), ('Property-sale gain', '− 10'), ('Simplified FFO', '= 80')]),
    'learn-affo': ('USD millions · dividend 60: 75% of 80; approximately 71.4% of 84', [('FFO', '100'), ('Straight-line rent + recurring expenditure', '− 8 − 12'), ('First AFFO view', '80'), ('With compensation add-back', '84')]),
    'learn-payout-ratio': ('Annual USD per share · dividend held at 3', [('AFFO 4.00', '75% payout'), ('AFFO 3.20', '93.75% payout'), ('AFFO 2.80', '107.1% payout')]),
    'learn-nav': ('USD per share · same NOI and claims', [('6% cap rate', '31.00 NAV'), ('7% cap rate', '≈ 23.86 NAV')]),
    'learn-bdc-nii-coverage': ('Same quarter · USD millions', [('Reported NII', '120'), ('Regular distributions', '100'), ('All distributions', '115'), ('Total coverage', '1.0435×')]),
    'learn-bdc-pik-income': ('Quarterly · USD millions · PIK 18 · different denominators', [('Total investment income 180', '10% PIK / TII'), ('Reported NII 120', '15% PIK / NII')]),
}


def format_for(a):
    slug = a.get('english_slug', a['slug'])
    if 'expert-' in slug:
        return 'workshop'
    if slug.endswith(('read-filings', 'checklist')):
        return 'workflow'
    if a.get('category') == 'Property sectors':
        return 'sector'
    if slug.endswith(('dividend-cuts', 'debt-maturities', 'interest-rates', 'non-accrual',
                      'leverage-coverage', 'rates-floors', 'dividends-tax')):
        return 'risk'
    if a.get('category') == 'Financial analysis' or slug.endswith((
            'nii-coverage', 'pik-income', 'nav-discounts', 'incentive-fees',
            'management-fees', 'yield-total-return', 'reinvestment')):
        return 'calculation'
    return 'concept'


def compose(body, a, spanish=False):
    """Reorganize existing semantic blocks rather than manufacture new claims."""
    kind = format_for(a)
    soup = BeautifulSoup(body, 'html.parser')
    article = soup.select_one('article.lesson-body')
    if article is None:
        raise ValueError('Missing lesson body: ' + a['slug'])
    wrapper = soup.new_tag('div', attrs={'class': ['lesson-edition', 'edition-' + kind],
                                       'data-reading-format': kind})
    for node in list(soup.contents):
        wrapper.append(node.extract())
    soup.append(wrapper)
    heading = wrapper.select_one('.education-heading')
    badge = soup.new_tag('p', attrs={'class': 'format-label'})
    es_labels = {'concept': 'Ensayo conceptual', 'calculation': 'Cuaderno de cálculo'}
    badge.string = es_labels.get(kind, 'Guía de estudio') if spanish else LABELS[kind][0]
    heading.insert(0, badge)

    # A compact jump menu replaces the identical tall sidebar on every lesson.
    toc = wrapper.select_one('.article-toc')
    if toc:
        toc.name = 'nav'
        toc['aria-label'] = 'On this page'
        toc['class'] = ['lesson-jump-menu']
        heading.find_next_sibling(class_='article-meta').insert_after(toc.extract())
        toc['class'].append('wrap')
    layout = wrapper.select_one('.reading-layout')
    if layout:
        layout['class'] = ['wrap', 'edition-layout']
    else:
        article['class'] = list(article.get('class', [])) + ['edition-layout']

    # Repeated full-width atlas/desk artwork made unrelated lessons look alike.
    # Keep an opening illustration only where it teaches the opening concept.
    visual = wrapper.select_one('.article-visual')
    if visual:
        if a['slug'] in ('learn-reit-basics', 'learn-reit-types'):
            visual['class'] = ['concept-illustration']
            first = article.find('section', recursive=False)
            first.insert_after(visual.extract())
        else:
            visual.decompose()

    sections = article.find_all('section', recursive=False)
    numbered = [s for s in sections if str(s.get('id', '')).startswith('section-')]
    if spanish:
        numbered = sections[:len(a['sections'])]
        for i, section in enumerate(numbered, 1):
            section['id'] = 'section-' + str(i)
    for i, section in enumerate(numbered, 1):
        section['class'] = list(section.get('class', [])) + ['editorial-section']
        mark = soup.new_tag('span', attrs={'class': 'section-index', 'aria-hidden': 'true'})
        mark.string = f'{i:02d}'
        section.insert(0, mark)

    example = article.select_one('.worked-example')
    if example and not spanish and a['slug'] in NUMBER_NOTES:
        caption, values = NUMBER_NOTES[a['slug']]
        figure = soup.new_tag('figure', attrs={'class': 'number-note'})
        label = soup.new_tag('figcaption')
        label.string = 'Hypothetical example · ' + caption
        figure.append(label)
        pairs = soup.new_tag('dl')
        for name, value in values:
            pair = soup.new_tag('div')
            term = soup.new_tag('dt'); term.string = name
            amount = soup.new_tag('dd'); amount.string = value
            pair.append(term); pair.append(amount); pairs.append(pair)
        figure.append(pairs)
        example.h2.insert_after(figure)
    pitfall = article.select_one('.pitfall')
    if kind in ('calculation', 'workshop') and example and numbered:
        # Workshop examples contain solved control totals. All assumptions and
        # analysis must precede them, including claims defined in later sections.
        anchor = numbered[0]
        if kind == 'workshop':
            numbered[-1].insert_after(example.extract())
        else:
            anchor.insert_after(example.extract())
        example['class'].append('notebook-example')
    if kind == 'risk' and pitfall and numbered:
        numbered[0].insert_after(pitfall.extract())
    if kind in ('sector', 'workflow') and numbered:
        group = soup.new_tag('div', attrs={'class': 'field-notes' if kind == 'sector' else 'filing-steps'})
        numbered[0].insert_before(group)
        for section in numbered:
            group.append(section.extract())
    if kind == 'workshop':
        for i, table in enumerate(article.select('.table-scroll'), 1):
            hint = soup.new_tag('p', attrs={'id': f'table-scroll-help-{i}', 'class': 'table-scroll-help'})
            hint.string = 'Scroll horizontally to see all columns. With the table focused, use the left and right arrow keys.'
            table.insert_before(hint)
            table['aria-describedby'] = hint['id']
            table['tabindex'] = '0'
        analysis = soup.new_tag('div', attrs={'class': 'workshop-analysis'})
        if numbered:
            numbered[0].insert_before(analysis)
            for section in numbered:
                analysis.append(section.extract())
    # Field notes pair cautions with disclosure checks; workshops pair the
    # open-ended problem with the short self-check instead of stacking both.
    remaining = article.find_all('section', recursive=False)
    checks = next((s for s in remaining if s.find('h2') and s.h2.get_text() == 'What to check in the disclosures'), None)
    if kind in ('sector', 'risk') and pitfall and checks:
        panel = soup.new_tag('div', attrs={'class': 'field-review'})
        pitfall.insert_before(panel)
        panel.append(pitfall.extract())
        panel.append(checks.extract())
    if kind == 'workshop':
        exercise = next((s for s in remaining if s.select_one('.workshop-answer')), None)
        quiz = next((s for s in remaining if s.select_one('[data-quiz]')), None)
        if exercise and quiz:
            panel = soup.new_tag('div', attrs={'class': 'workshop-practice'})
            exercise.insert_before(panel)
            panel.append(exercise.extract())
            panel.append(quiz.extract())
    if spanish and not toc:
        toc = soup.new_tag('nav', attrs={'class': ['lesson-jump-menu', 'wrap'], 'aria-label': 'En esta página'})
        listing = soup.new_tag('ol')
        for i, section in enumerate(article.find_all('section', recursive=False), 1):
            if not section.find('h2'):
                continue
            if not section.get('id'):
                section['id'] = 'reading-' + str(i)
            item = soup.new_tag('li')
            link = soup.new_tag('a', href='#' + section['id'])
            link.string = section.h2.get_text()
            item.append(link); listing.append(item)
        toc.append(listing)
        article.insert_before(toc)
    if toc:
        order = {node['id']: i for i, node in enumerate(article.select('[id]'))}
        listing = toc.find('ol')
        for item in sorted(listing.find_all('li', recursive=False),
                           key=lambda item: order.get(item.a['href'].lstrip('#'), 999)):
            listing.append(item.extract())
    # Keep every source, limitation, exercise and quiz accessible in the document.
    return str(soup)
