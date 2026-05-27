import React, { useState, useEffect } from 'react';
import { getNotificationRules, createNotificationRule, deleteNotificationRule, type NotificationRule } from '../api';

export const NotificationSettings: React.FC = () => {
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [name, setName] = useState('');
  const [channelType, setChannelType] = useState<'webhook' | 'email'>('webhook');
  const [target, setTarget] = useState('');
  const [severity, setSeverity] = useState<'HIGH' | 'CRITICAL'>('CRITICAL');
  const [loading, setLoading] = useState(false);

  // Fetch rules on mount
  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const data = await getNotificationRules();
      setRules(data.rules || []);
    } catch (err) {
      console.error("Failed to fetch notification rules", err);
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !target) return;

    setLoading(true);
    try {
      await createNotificationRule({
        name,
        channel_type: channelType,
        target_url_or_email: target,
        severity_threshold: severity,
        is_active: true
      });

      // Reset form & reload list
      setName('');
      setTarget('');
      fetchRules();
    } catch (err) {
      console.error("Failed to create rule", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (id: string) => {
    try {
      await deleteNotificationRule(id);
      fetchRules();
    } catch (err) {
      console.error("Failed to delete rule", err);
    }
  };

  return (
    <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
      <div className="space-y-2">
        <h2 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Notification Channels</h2>
        <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">Configure alerting workflows for high and critical findings.</p>
      </div>

      {/* Rule Form */}
      <form onSubmit={handleCreateRule} className="space-y-4 p-4 border-4 border-black bg-black/20">
        <div>
          <label className="block text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] mb-2">Rule Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full bg-black/40 border-2 border-black p-2 text-xs font-mono text-rag-blue font-bold focus:outline-none" placeholder="Production Alerts" />
        </div>
        <div>
          <label className="block text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] mb-2">Channel Type</label>
          <select value={channelType} onChange={(e) => setChannelType(e.target.value as 'webhook' | 'email')} className="w-full bg-black/40 border-2 border-black p-2 text-xs font-mono text-rag-blue font-bold focus:outline-none">
            <option value="webhook">Webhook</option>
            <option value="email">Email</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] mb-2">
            {channelType === 'webhook' ? 'Webhook Endpoint URL' : 'Target Email Address'}
          </label>
          <input type="text" value={target} onChange={(e) => setTarget(e.target.value)} className="w-full bg-black/40 border-2 border-black p-2 text-xs font-mono text-rag-blue font-bold focus:outline-none" placeholder={channelType === 'webhook' ? 'https://hooks.slack.com/...' : 'admin@company.com'} />
        </div>
        <div>
          <label className="block text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] mb-2">Severity Threshold</label>
          <select value={severity} onChange={(e) => setSeverity(e.target.value as 'HIGH' | 'CRITICAL')} className="w-full bg-black/40 border-2 border-black p-2 text-xs font-mono text-rag-blue font-bold focus:outline-none">
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High & Critical</option>
          </select>
        </div>
        <button type="submit" disabled={loading} className="w-full py-3 bg-rag-blue text-black text-[10px] font-black uppercase tracking-[0.2em] hover:bg-rag-blue/90 transition-all">
          {loading ? 'SAVING...' : 'ADD CHANNEL'}
        </button>
      </form>

      {/* Active Rules List */}
      <div className="space-y-4">
        <h3 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.4em] italic border-b-2 border-black pb-2">Configured Channels</h3>
        <div className="space-y-2">
          {rules.length === 0 ? (
            <p className="text-[9px] text-silver/40 italic font-mono">No alerting channels configured yet.</p>
          ) : (
            rules.map((rule) => (
              <div key={rule.id} className="flex justify-between items-center p-3 border-2 border-black bg-black/20">
                <div>
                  <div className="text-[10px] font-bold text-silver-bright">{rule.name}</div> 
                  <div className="flex gap-2 mt-1">
                    <span className="text-[8px] px-1.5 bg-black text-silver uppercase">{rule.channel_type}</span>
                    <span className="text-[8px] px-1.5 bg-rag-red text-black font-bold uppercase">{rule.severity_threshold}+</span>
                  </div>
                  <div className="text-[9px] text-silver/40 font-mono mt-1 break-all">{rule.target_url_or_email}</div>
                </div>
                <button onClick={() => rule.id && handleDeleteRule(rule.id)} className="text-rag-red hover:text-white text-[10px] font-bold uppercase">
                  DELETE
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
