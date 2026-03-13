const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '../..');
const helpers = require(path.join(repoRoot, 'web/static/js/app_selection_visibility_helpers.js'));

test('resolvePresetActionState toggles disabled state from preset selection', () => {
    assert.deepEqual(helpers.resolvePresetActionState('preset-1'), {
        hasSelection: true,
        disabled: false,
        inactiveClasses: ['opacity-50', 'cursor-not-allowed']
    });

    assert.deepEqual(helpers.resolvePresetActionState(''), {
        hasSelection: false,
        disabled: true,
        inactiveClasses: ['opacity-50', 'cursor-not-allowed']
    });
});

test('archive selection helpers render placeholders and selected entries', () => {
    assert.match(
        helpers.buildSelectedArchiveReferencesHtml([]),
        /선택된 참고본이 없습니다/
    );

    const html = helpers.buildSelectedArchiveReferencesHtml([
        {
            job_id: 'job-1',
            title: 'Newsletter One',
            snippet: 'snippet',
            source_value: 'source'
        }
    ]);

    assert.match(html, /Newsletter One/);
    assert.match(html, /snippet/);
    assert.match(html, /app\.removeArchiveReference\('job-1'\)/);
});

test('archive search result helper reflects selected state and button label', () => {
    const html = helpers.buildArchiveSearchResultsHtml(
        [
            {
                job_id: 'job-1',
                title: 'Newsletter One',
                snippet: 'snippet',
                source_value: 'source'
            }
        ],
        [{ job_id: 'job-1' }]
    );

    assert.match(html, /Newsletter One/);
    assert.match(html, /선택 해제/);
    assert.match(html, /bg-red-100 text-red-700 hover:bg-red-200/);
});

test('resolveArchiveSelectionUpdate handles add, remove, limit, and missing search item', () => {
    assert.deepEqual(
        helpers.resolveArchiveSelectionUpdate({
            selectedArchiveReferences: [{ job_id: 'job-1' }],
            archiveSearchResults: [{ job_id: 'job-1', title: 'one' }],
            jobId: 'job-1'
        }),
        {
            nextSelectedReferences: [],
            operation: 'removed'
        }
    );

    const addResult = helpers.resolveArchiveSelectionUpdate({
        selectedArchiveReferences: [{ job_id: 'job-1' }],
        archiveSearchResults: [{ job_id: 'job-2', title: 'two' }],
        jobId: 'job-2'
    });
    assert.equal(addResult.operation, 'added');
    assert.equal(addResult.nextSelectedReferences.length, 2);
    assert.equal(addResult.statusMessage, '2개의 참고본을 선택했습니다.');
    assert.equal(addResult.statusTone, 'green');

    assert.equal(
        helpers.resolveArchiveSelectionUpdate({
            selectedArchiveReferences: [{ job_id: '1' }, { job_id: '2' }, { job_id: '3' }],
            archiveSearchResults: [{ job_id: '4', title: 'four' }],
            jobId: '4'
        }).error,
        '과거 뉴스레터 참고본은 최대 3개까지 선택할 수 있습니다.'
    );

    assert.equal(
        helpers.resolveArchiveSelectionUpdate({
            selectedArchiveReferences: [],
            archiveSearchResults: [],
            jobId: 'missing'
        }).error,
        '선택한 참고본 정보를 찾을 수 없습니다.'
    );
});

test('resolveTabPanelState maps tab ids to panel ids and load actions', () => {
    assert.deepEqual(helpers.resolveTabPanelState('analyticsTab'), {
        panelId: 'analyticsPanel',
        loadAction: 'analytics'
    });
    assert.deepEqual(helpers.resolveTabPanelState('generateTab'), {
        panelId: 'generatePanel',
        loadAction: null
    });
    assert.deepEqual(helpers.resolveTabPanelState('unknown'), {
        panelId: null,
        loadAction: null
    });
});

test('resolveInputMethodVisibility and resolveScheduleViewState preserve UI shell semantics', () => {
    assert.deepEqual(helpers.resolveInputMethodVisibility('keywords'), {
        keywordsHidden: false,
        domainHidden: true
    });
    assert.deepEqual(helpers.resolveInputMethodVisibility('domain'), {
        keywordsHidden: true,
        domainHidden: false
    });

    assert.deepEqual(
        helpers.resolveScheduleViewState({ enabled: false, frequency: 'DAILY' }),
        {
            scheduleSettingsHidden: true,
            weeklyOptionsHidden: true,
            generateButtonHtml: '<i class="fas fa-play mr-2"></i>생성하기'
        }
    );

    assert.deepEqual(
        helpers.resolveScheduleViewState({ enabled: true, frequency: 'WEEKLY' }),
        {
            scheduleSettingsHidden: false,
            weeklyOptionsHidden: false,
            generateButtonHtml: '<i class="fas fa-calendar-plus mr-2"></i>예약 저장'
        }
    );
});

test('status class helpers return stable classnames for UI sections', () => {
    assert.equal(
        helpers.buildPresetStatusClassName('green'),
        'mt-2 text-sm text-green-600'
    );
    assert.equal(
        helpers.buildArchiveStatusClassName('yellow'),
        'text-sm text-amber-600'
    );
    assert.equal(
        helpers.buildAnalyticsStatusClassName('red'),
        'mt-4 rounded-lg border px-4 py-3 text-sm border-red-200 bg-red-50 text-red-700'
    );
});

test('index templates load all JS helper scripts before app shell', () => {
    ['index.html', 'index_en.html'].forEach((templateName) => {
        const template = fs.readFileSync(path.join(repoRoot, 'web/templates', templateName), 'utf8');
        const requestHelpersIndex = template.indexOf('js/app_request_response_helpers.js');
        const viewHelpersIndex = template.indexOf('js/app_view_state_helpers.js');
        const selectionHelpersIndex = template.indexOf('js/app_selection_visibility_helpers.js');
        const appIndex = template.indexOf('js/app.js');

        assert.notEqual(requestHelpersIndex, -1, `${templateName} should load request helper`);
        assert.notEqual(viewHelpersIndex, -1, `${templateName} should load view-state helper`);
        assert.notEqual(selectionHelpersIndex, -1, `${templateName} should load selection helper`);
        assert.notEqual(appIndex, -1, `${templateName} should load app shell`);
        assert.ok(requestHelpersIndex < appIndex, `${templateName} should load request helper before app.js`);
        assert.ok(viewHelpersIndex < appIndex, `${templateName} should load view helper before app.js`);
        assert.ok(selectionHelpersIndex < appIndex, `${templateName} should load selection helper before app.js`);
    });
});
