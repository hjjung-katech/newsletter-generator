const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '../..');
const helpers = require(path.join(repoRoot, 'web/static/js/app_request_response_helpers.js'));

test('buildGenerationRequest builds keyword payload with weekly schedule', () => {
    const result = helpers.buildGenerationRequest({
        method: 'keywords',
        keywordsInput: 'AI, Battery , Robotics',
        emailInput: 'ops@example.com',
        periodValue: '14',
        templateStyle: 'compact',
        emailCompatible: true,
        archiveReferenceIds: ['job-1', 'job-2'],
        enableSchedule: true,
        frequency: 'WEEKLY',
        scheduleTime: '09:30',
        selectedWeekdays: ['MO', 'WE']
    }, {
        includeSchedule: true,
        includeEmail: true
    });

    assert.equal(result.error, undefined);
    assert.deepEqual(result.data, {
        keywords: ['AI', 'Battery', 'Robotics'],
        email: 'ops@example.com',
        period: 14,
        template_style: 'compact',
        email_compatible: true,
        archive_reference_ids: ['job-1', 'job-2'],
        rrule: 'FREQ=WEEKLY;BYDAY=MO,WE;BYHOUR=09;BYMINUTE=30',
        schedule: true
    });
});

test('buildGenerationRequest preserves domain flow and validates required fields', () => {
    assert.deepEqual(
        helpers.buildGenerationRequest({
            method: 'domain',
            domainInput: 'AI',
            emailInput: '',
            periodValue: '7',
            templateStyle: 'modern',
            emailCompatible: false,
            archiveReferenceIds: []
        }, {
            includeSchedule: false,
            includeEmail: false
        }),
        {
            data: {
                domain: 'AI',
                period: 7,
                template_style: 'modern',
                email_compatible: false
            }
        }
    );

    assert.deepEqual(
        helpers.buildGenerationRequest({
            method: 'keywords',
            keywordsInput: '   '
        }),
        { error: '키워드를 입력해주세요.' }
    );

    assert.deepEqual(
        helpers.buildGenerationRequest({
            method: 'keywords',
            keywordsInput: 'AI',
            enableSchedule: true,
            frequency: 'WEEKLY',
            scheduleTime: '10:00',
            selectedWeekdays: ['TU']
        }),
        { error: '예약 발송을 위해서는 이메일 주소가 필요합니다.' }
    );
});

test('preset and source policy payload helpers preserve trimming and validation', () => {
    assert.deepEqual(
        helpers.buildPresetPayload({
            params: { keywords: ['AI'] },
            name: '  Morning Brief  ',
            description: '  daily preset  ',
            isDefault: true
        }),
        {
            payload: {
                name: 'Morning Brief',
                description: 'daily preset',
                is_default: true,
                params: { keywords: ['AI'] }
            }
        }
    );

    assert.deepEqual(
        helpers.buildSourcePolicyPayload({
            pattern: '  example.com  ',
            policyType: 'allow',
            isActive: 1
        }),
        {
            payload: {
                pattern: 'example.com',
                policy_type: 'allow',
                is_active: true
            }
        }
    );

    assert.deepEqual(
        helpers.buildSourcePolicyPayload({
            pattern: '   ',
            policyType: 'allow',
            isActive: true
        }),
        { error: '소스 패턴을 입력해주세요.' }
    );
});

test('normalizeGenerationResultEnvelope merges top-level metadata without mutating shell contract', () => {
    const normalized = helpers.normalizeGenerationResultEnvelope({
        sent: false,
        approval_status: 'approved',
        delivery_status: 'sent',
        approved_at: '2026-03-12T00:00:00Z',
        approval_note: 'ready',
        result: {
            html_content: '<html>ok</html>',
            status: 'success'
        }
    }, 'job-123');

    assert.deepEqual(normalized, {
        html_content: '<html>ok</html>',
        status: 'success',
        job_id: 'job-123',
        sent: false,
        approval_status: 'approved',
        delivery_status: 'sent',
        approved_at: '2026-03-12T00:00:00Z',
        approval_note: 'ready'
    });
});

test('buildResultDetailsHtml renders delivery, stats, input params, and iframe sections', () => {
    const html = helpers.buildResultDetailsHtml({
        job_id: 'job-123',
        html_content: '<html>ok</html>',
        html_size: 4096,
        approval_status: 'approved',
        delivery_status: 'sent',
        approved_at: '2026-03-12T00:00:00Z',
        approval_note: 'ship it',
        generation_stats: {
            total_time: 3.21,
            articles_count: 5,
            generated_keywords: 'AI, Robotics',
            step_times: {
                collect: 1.2,
                summarize: 2.01
            }
        },
        processing_info: {
            using_real_cli: false,
            template_style: 'compact',
            email_compatible: true,
            period_days: 14
        },
        input_params: {
            keywords: 'AI, Robotics',
            domain: 'Mobility'
        },
        archive_references: [
            {
                title: 'Prior Run',
                source_value: 'archive/job-1',
                job_id: 'job-1'
            }
        ]
    });

    assert.match(html, /Delivery Review/);
    assert.match(html, /Generation Statistics/);
    assert.match(html, /Generated Keywords/);
    assert.match(html, /Processing Information/);
    assert.match(html, /Input Parameters/);
    assert.match(html, /Archive References/);
    assert.match(html, /newsletter-html\/job-123/);
    assert.match(html, /Approval: 승인 완료/);
});

test('index templates load helper before app shell', () => {
    ['index.html', 'index_en.html'].forEach((templateName) => {
        const template = fs.readFileSync(path.join(repoRoot, 'web/templates', templateName), 'utf8');
        const helperIndex = template.indexOf('js/app_request_response_helpers.js');
        const appIndex = template.indexOf('js/app.js');

        assert.notEqual(helperIndex, -1, `${templateName} should load helper script`);
        assert.notEqual(appIndex, -1, `${templateName} should load app shell`);
        assert.ok(helperIndex < appIndex, `${templateName} should load helper before app.js`);
    });
});
