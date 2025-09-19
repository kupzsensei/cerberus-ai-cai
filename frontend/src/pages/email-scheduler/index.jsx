import React, { useState } from "react";
import { getEmailConfigs, getEmailRecipientGroups, getScheduledResearchList } from "../../api/apiService";
import EmailConfigSection from "./EmailConfigSection";
import RecipientGroupSection from "./RecipientGroupSection";
import ScheduledResearchSection from "./ScheduledResearchSection";
import EmailDeliveryLogsSection from "./EmailDeliveryLogsSection";

const EmailSchedulerPage = () => {
  const [activeTab, setActiveTab] = useState("scheduled-research");
  const [emailConfigs, setEmailConfigs] = useState([]);
  const [recipientGroups, setRecipientGroups] = useState([]);
  const [scheduledResearch, setScheduledResearch] = useState([]);

  // Function to refresh all data
  const refreshData = async () => {
    try {
      const configs = await getEmailConfigs();
      setEmailConfigs(configs);
      
      const groups = await getEmailRecipientGroups();
      setRecipientGroups(groups);
      
      const research = await getScheduledResearchList();
      setScheduledResearch(research);
    } catch (error) {
      console.error("Error refreshing data:", error);
    }
  };

  // Load data on component mount
  React.useEffect(() => {
    refreshData();
  }, []);

  return (
    <div className="page-content text-green-500 border-b p-5">
      <h1 className="font-bold text-2xl mb-5">Email Scheduler</h1>
      <p className="mb-5">Configure automated threat research reports to be sent via email.</p>

      {/* Tab Navigation */}
      <div className="flex border-b border-green-500 mb-5">
        <button
          className={`py-2 px-4 font-semibold ${activeTab === "scheduled-research" ? "text-green-500 border-b-2 border-green-500" : "text-green-700 hover:text-green-500"}`}
          onClick={() => setActiveTab("scheduled-research")}
        >
          Scheduled Research
        </button>
        <button
          className={`py-2 px-4 font-semibold ${activeTab === "email-config" ? "text-green-500 border-b-2 border-green-500" : "text-green-700 hover:text-green-500"}`}
          onClick={() => setActiveTab("email-config")}
        >
          Email Configuration
        </button>
        <button
          className={`py-2 px-4 font-semibold ${activeTab === "recipient-groups" ? "text-green-500 border-b-2 border-green-500" : "text-green-700 hover:text-green-500"}`}
          onClick={() => setActiveTab("recipient-groups")}
        >
          Recipient Groups
        </button>
        <button
          className={`py-2 px-4 font-semibold ${activeTab === "delivery-logs" ? "text-green-500 border-b-2 border-green-500" : "text-green-700 hover:text-green-500"}`}
          onClick={() => setActiveTab("delivery-logs")}
        >
          Delivery Logs
        </button>
      </div>

      {/* Tab Content */}
      <div className="mt-5">
        {activeTab === "scheduled-research" && (
          <ScheduledResearchSection 
            scheduledResearch={scheduledResearch} 
            recipientGroups={recipientGroups}
            emailConfigs={emailConfigs}
            onRefresh={refreshData}
          />
        )}
        
        {activeTab === "email-config" && (
          <EmailConfigSection 
            emailConfigs={emailConfigs} 
            onRefresh={refreshData}
          />
        )}
        
        {activeTab === "recipient-groups" && (
          <RecipientGroupSection 
            recipientGroups={recipientGroups} 
            onRefresh={refreshData}
          />
        )}
        
        {activeTab === "delivery-logs" && (
          <EmailDeliveryLogsSection 
            scheduledResearch={scheduledResearch}
            onRefresh={refreshData}
          />
        )}
      </div>
    </div>
  );
};

export default EmailSchedulerPage;