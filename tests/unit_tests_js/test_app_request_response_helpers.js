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
        personalization_visibility: {
            personalization_state: 'default',
            status_label: '기본 개인화'
        },
        effective_settings_provenance: {
            effective_state: 'default',
            status_label: '기본 설정 조합'
        },
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
        approval_note: 'ready',
        personalization_visibility: {
            personalization_state: 'default',
            status_label: '기본 개인화'
        },
        effective_settings_provenance: {
            effective_state: 'default',
            status_label: '기본 설정 조합'
        }
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
        personalization_visibility: {
            personalization_state: 'overridden',
            status_label: '오버라이드 적용',
            status_message: '기본값 대비 개인화 오버라이드 2개가 적용됩니다.',
            effective_template_style: 'compact',
            effective_period: 14,
            email_mode_label: '이메일 호환 모드',
            override_labels: ['이메일 호환 모드', '아카이브 컨텍스트'],
            archive_reference_count: 1,
            source_policy_message: '활성 소스 정책 1개와 연결됩니다.'
        },
        effective_settings_provenance: {
            effective_state: 'overridden',
            status_label: '오버라이드된 설정 조합',
            status_message: '기본값 대비 오버라이드가 적용된 현재 설정 조합을 기준으로 결과를 해석할 수 있습니다.',
            diagnostics: {
                primary_reason_code: 'personalization_overridden_but_unlinked',
                reason_codes: ['personalization_overridden_but_unlinked'],
                summary: '개인화 override는 있지만 preset/source policy linkage가 연결되지 않아 override가 현재 결과에 그대로 반영됐는지 즉시 확인하기 어렵습니다.',
                details: [
                    '개인화 override는 있지만 preset/source policy linkage가 연결되지 않아 override가 현재 결과에 그대로 반영됐는지 즉시 확인하기 어렵습니다.'
                ],
                field_summary: '개인화 축에서 override는 있으나 연결 상태가 linked가 아닙니다.',
                field_explanations: [
                    {
                        axis: 'personalization',
                        axis_label: '개인화',
                        field: 'source_policy_link_state',
                        field_label: '개인화 연결 상태',
                        expected_value: 'linked',
                        current_value: 'unknown',
                        expected_label: 'override가 연결된 상태로 반영됨',
                        current_label: '연결 상태 미상',
                        summary: '개인화 축에서 override는 있으나 연결 상태가 linked가 아닙니다.',
                        detail: 'override 2개(이메일 호환 모드, 아카이브 컨텍스트)가 있지만 현재 linkage는 \'연결 상태 미상\' 이어서 현재 결과 반영 여부를 즉시 확정하기 어렵습니다.'
                    }
                ]
            },
            preset_name: 'Morning Brief',
            preset_is_default: true,
            default_mode_label: '오버라이드 적용',
            personalization_label: '오버라이드 적용',
            source_policy_label: '활성 정책 연결',
            summary_tokens: [
                '프리셋: Morning Brief (기본)',
                '개인화: 오버라이드 적용',
                '기본값/오버라이드: 오버라이드 적용',
                '소스 정책: 활성 정책 연결'
            ],
            recent_execution_timestamp: '2026-03-12T00:00:00Z'
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
    assert.match(html, /Effective Settings Provenance/);
    assert.match(html, /오버라이드된 설정 조합/);
    assert.match(html, /진단: 개인화 override는 있지만/);
    assert.match(html, /차이 축: 개인화 축에서 override는 있으나 연결 상태가 linked가 아닙니다/);
    assert.match(html, /세부: override 2개\(이메일 호환 모드, 아카이브 컨텍스트\)가 있지만 현재 linkage는 '연결 상태 미상' 이어서/);
    assert.match(html, /프리셋: Morning Brief \(기본\)/);
    assert.match(html, /Personalization Context/);
    assert.match(html, /오버라이드 적용/);
    assert.match(html, /Overrides: 이메일 호환 모드, 아카이브 컨텍스트/);
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
