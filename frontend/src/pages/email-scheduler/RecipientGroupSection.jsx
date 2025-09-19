import React, { useState, useEffect } from "react";
import { addEmailRecipientGroup, updateEmailRecipientGroup, deleteEmailRecipientGroup, 
         addEmailRecipient, updateEmailRecipient, deleteEmailRecipient, 
         getEmailRecipients } from "../../api/apiService";

const RecipientGroupSection = ({ recipientGroups, onRefresh }) => {
  const [expandedGroup, setExpandedGroup] = useState(null);
  const [groupRecipients, setGroupRecipients] = useState({});
  const [isAddingGroup, setIsAddingGroup] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [isAddingRecipient, setIsAddingRecipient] = useState(null); // Group ID or null
  const [editingRecipient, setEditingRecipient] = useState(null);
  
  const [groupFormData, setGroupFormData] = useState({
    name: "",
    description: ""
  });
  
  const [recipientFormData, setRecipientFormData] = useState({
    email: "",
    name: ""
  });

  // Load recipients for expanded groups
  useEffect(() => {
    const loadRecipients = async () => {
      if (expandedGroup) {
        try {
          const recipients = await getEmailRecipients(expandedGroup);
          setGroupRecipients(prev => ({
            ...prev,
            [expandedGroup]: recipients
          }));
        } catch (error) {
          console.error("Error loading recipients:", error);
        }
      }
    };
    
    loadRecipients();
  }, [expandedGroup]);

  const handleAddNewGroup = () => {
    setIsAddingGroup(true);
    setEditingGroup(null);
    setGroupFormData({
      name: "",
      description: ""
    });
  };

  const handleEditGroup = (group) => {
    setEditingGroup(group);
    setIsAddingGroup(false);
    setGroupFormData({
      name: group.name || "",
      description: group.description || ""
    });
  };

  const handleDeleteGroup = async (groupId) => {
    if (window.confirm("Are you sure you want to delete this recipient group? This will also delete all recipients in this group.")) {
      try {
        await deleteEmailRecipientGroup(groupId);
        if (expandedGroup === groupId) {
          setExpandedGroup(null);
        }
        onRefresh();
      } catch (error) {
        console.error("Error deleting recipient group:", error);
        alert("Failed to delete recipient group: " + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleGroupFormChange = (e) => {
    const { name, value } = e.target;
    setGroupFormData({
      ...groupFormData,
      [name]: value
    });
  };

  const handleGroupFormSubmit = async (e) => {
    e.preventDefault();
    try {
      const form = new FormData();
      form.append("name", groupFormData.name);
      form.append("description", groupFormData.description);

      if (editingGroup) {
        await updateEmailRecipientGroup(editingGroup.id, form);
      } else {
        await addEmailRecipientGroup(form);
      }
      
      setIsAddingGroup(false);
      setEditingGroup(null);
      onRefresh();
    } catch (error) {
      console.error("Error saving recipient group:", error);
      alert("Failed to save recipient group: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleGroupFormCancel = () => {
    setIsAddingGroup(false);
    setEditingGroup(null);
  };

  const toggleGroupExpansion = (groupId) => {
    setExpandedGroup(expandedGroup === groupId ? null : groupId);
  };

  const handleAddNewRecipient = (groupId) => {
    setIsAddingRecipient(groupId);
    setEditingRecipient(null);
    setRecipientFormData({
      email: "",
      name: ""
    });
  };

  const handleEditRecipient = (recipient) => {
    setEditingRecipient(recipient);
    setIsAddingRecipient(null);
    setRecipientFormData({
      email: recipient.email || "",
      name: recipient.name || ""
    });
  };

  const handleDeleteRecipient = async (recipientId, groupId) => {
    if (window.confirm("Are you sure you want to delete this recipient?")) {
      try {
        await deleteEmailRecipient(recipientId);
        // Refresh recipients for this group
        const recipients = await getEmailRecipients(groupId);
        setGroupRecipients(prev => ({
          ...prev,
          [groupId]: recipients
        }));
      } catch (error) {
        console.error("Error deleting recipient:", error);
        alert("Failed to delete recipient: " + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleRecipientFormChange = (e) => {
    const { name, value } = e.target;
    setRecipientFormData({
      ...recipientFormData,
      [name]: value
    });
  };

  const handleRecipientFormSubmit = async (e, groupId) => {
    e.preventDefault();
    try {
      const form = new FormData();
      form.append("email", recipientFormData.email);
      form.append("name", recipientFormData.name);
      
      if (editingRecipient) {
        form.append("group_id", editingRecipient.group_id);
        await updateEmailRecipient(editingRecipient.id, form);
      } else {
        form.append("group_id", groupId);
        await addEmailRecipient(form);
      }
      
      setIsAddingRecipient(null);
      setEditingRecipient(null);
      
      // Refresh recipients for this group
      const recipients = await getEmailRecipients(groupId);
      setGroupRecipients(prev => ({
        ...prev,
        [groupId]: recipients
      }));
    } catch (error) {
      console.error("Error saving recipient:", error);
      alert("Failed to save recipient: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleRecipientFormCancel = () => {
    setIsAddingRecipient(null);
    setEditingRecipient(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Recipient Groups</h2>
        <button
          className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
          onClick={handleAddNewGroup}
        >
          Add New Group
        </button>
      </div>

      {(isAddingGroup || editingGroup) && (
        <div className="bg-green-900/30 border border-green-700 rounded p-4 mb-6">
          <h3 className="text-lg font-bold mb-3">
            {editingGroup ? "Edit Recipient Group" : "Add New Recipient Group"}
          </h3>
          <form onSubmit={handleGroupFormSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Group Name *</label>
                <input
                  type="text"
                  name="name"
                  value={groupFormData.name}
                  onChange={handleGroupFormChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input
                  type="text"
                  name="description"
                  value={groupFormData.description}
                  onChange={handleGroupFormChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                />
              </div>
            </div>

            <div className="flex space-x-2">
              <button
                type="submit"
                className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
              >
                {editingGroup ? "Update Group" : "Add Group"}
              </button>
              <button
                type="button"
                className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded"
                onClick={handleGroupFormCancel}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {recipientGroups.map((group) => (
          <div key={group.id} className="bg-green-900/30 border border-green-700 rounded">
            <div 
              className="flex justify-between items-center p-4 cursor-pointer hover:bg-green-800/30"
              onClick={() => toggleGroupExpansion(group.id)}
            >
              <div>
                <h3 className="font-bold text-lg">{group.name}</h3>
                {group.description && (
                  <p className="text-green-300 text-sm">{group.description}</p>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm bg-green-800/50 px-2 py-1 rounded">
                  {groupRecipients[group.id]?.length || 0} recipients
                </span>
                <button
                  className="text-blue-400 hover:text-blue-300 mr-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditGroup(group);
                  }}
                >
                  Edit
                </button>
                <button
                  className="text-red-400 hover:text-red-300 mr-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteGroup(group.id);
                  }}
                >
                  Delete
                </button>
                <span className="text-xl">
                  {expandedGroup === group.id ? "▼" : "▶"}
                </span>
              </div>
            </div>
            
            {expandedGroup === group.id && (
              <div className="border-t border-green-700 p-4">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="font-bold">Recipients</h4>
                  <button
                    className="bg-green-700 hover:bg-green-600 text-white py-1 px-3 rounded text-sm"
                    onClick={() => handleAddNewRecipient(group.id)}
                  >
                    Add Recipient
                  </button>
                </div>
                
                {(isAddingRecipient === group.id || editingRecipient?.group_id === group.id) && (
                  <div className="bg-green-800/30 border border-green-600 rounded p-3 mb-4">
                    <h5 className="font-bold mb-2">
                      {editingRecipient ? "Edit Recipient" : "Add New Recipient"}
                    </h5>
                    <form onSubmit={(e) => handleRecipientFormSubmit(e, group.id)}>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block text-sm font-medium mb-1">Email *</label>
                          <input
                            type="email"
                            name="email"
                            value={recipientFormData.email}
                            onChange={handleRecipientFormChange}
                            className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Name</label>
                          <input
                            type="text"
                            name="name"
                            value={recipientFormData.name}
                            onChange={handleRecipientFormChange}
                            className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                          />
                        </div>
                      </div>

                      <div className="flex space-x-2">
                        <button
                          type="submit"
                          className="bg-green-700 hover:bg-green-600 text-white py-1 px-3 rounded text-sm"
                        >
                          {editingRecipient ? "Update Recipient" : "Add Recipient"}
                        </button>
                        <button
                          type="button"
                          className="bg-gray-700 hover:bg-gray-600 text-white py-1 px-3 rounded text-sm"
                          onClick={handleRecipientFormCancel}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                )}
                
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="bg-green-800/50">
                        <th className="py-2 px-4 text-left">Name</th>
                        <th className="py-2 px-4 text-left">Email</th>
                        <th className="py-2 px-4 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {groupRecipients[group.id]?.map((recipient) => (
                        <tr key={recipient.id} className="border-t border-green-700 hover:bg-green-800/30">
                          <td className="py-2 px-4">{recipient.name || "-"}</td>
                          <td className="py-2 px-4">{recipient.email}</td>
                          <td className="py-2 px-4">
                            <button
                              className="text-blue-400 hover:text-blue-300 mr-2"
                              onClick={() => handleEditRecipient(recipient)}
                            >
                              Edit
                            </button>
                            <button
                              className="text-red-400 hover:text-red-300"
                              onClick={() => handleDeleteRecipient(recipient.id, group.id)}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                      {(!groupRecipients[group.id] || groupRecipients[group.id].length === 0) && (
                        <tr>
                          <td colSpan="3" className="py-4 px-4 text-center">
                            No recipients in this group.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
        
        {recipientGroups.length === 0 && (
          <div className="text-center py-8 text-green-300">
            No recipient groups found. Add a new group to get started.
          </div>
        )}
      </div>
    </div>
  );
};

export default RecipientGroupSection;