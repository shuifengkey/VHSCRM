log = {"ten_cty":"Test", "ky_thuat_vien":"KTV", "checkin_time": "2026-05-25T13:00:00", "checkout_time": "2026-05-25T13:30:00"}
dur = "30m"
warn = False
status_icon = "x"
left_color = "green"
att_html = ""
try:
    s = f"""<div style="background:white;border:1px solid #e2e8f0;border-left:4px solid {left_color};
                border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
                <span style="font-size:15px;font-weight:700;color:#0f172a;">{status_icon} {log['ten_cty']}</span>
                {'<span style="font-size:10px;background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:8px;margin-left:8px;font-weight:700;">⚠️ SAI GIỜ</span>' if warn else ''}
                <div style="font-size:12px;color:#64748b;margin-top:3px;">
                    👷 {log['ky_thuat_vien'] or '-'} &nbsp;·&nbsp;
                    🕐 {log['checkin_time'][11:16] if log['checkin_time'] else '-'} →
                    {log['checkout_time'][11:16] if log['checkout_time'] else '...'}
                    &nbsp;{dur}
                </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
                <div style="font-size:11px;color:#94a3b8;">{log['checkin_time'][:10] if log['checkin_time'] else ''}</div>
                {('<div style="display:flex;">' + att_html + '</div>') if att_html else ''}
            </div>
        </div>
    </div>"""
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
