import { AlertTriangle, CheckCircle2, CircleDotDashed } from "lucide-react";

import type { TraceStep } from "../lib/types";

type ToolTraceProps = {
  trace: TraceStep[];
  changeLog: string[];
};

export function ToolTrace({ trace, changeLog }: ToolTraceProps) {
  return (
    <section className="panel trace-panel" id="trace">
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Tool Trace</p>
          <h2>工具调用链</h2>
        </div>
        <CircleDotDashed size={20} aria-hidden="true" />
      </div>

      <div className="trace-list">
        {trace.map((step) => {
          const Icon = step.status === "warn" ? AlertTriangle : CheckCircle2;
          return (
            <div className={`trace-step ${step.status}`} key={`${step.step}-${step.tool}`}>
              <Icon size={18} aria-hidden="true" />
              <div>
                <div className="trace-title">
                  <span>{step.step}</span>
                  <strong>{step.tool}</strong>
                </div>
                <p>{step.detail}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="change-log">
        <h3>状态更新</h3>
        {changeLog.map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>
    </section>
  );
}
