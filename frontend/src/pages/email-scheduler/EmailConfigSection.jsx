import React, { useState } from "react";
import { addEmailConfig, updateEmailConfig, deleteEmailConfig } from "../../api/apiService";

const EmailConfigSection = ({ emailConfigs, onRefresh }) => {
  const [isAdding, setIsAdding] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [formData, setFormData] = useState({
    smtp_server: "",
    smtp_port: 587,
    username: "",
    password: "",
    sender_email: "",
    sender_name: "",
    use_tls: true,
    use_ssl: false
  });

  const handleAddNew = () => {
    setIsAdding(true);
    setEditingConfig(null);
    setFormData({
      smtp_server: "",
      smtp_port: 587,
      username: "",
      password: "",
      sender_email: "",
      sender_name: "",
      use_tls: true,
      use_ssl: false
    });
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setIsAdding(false);
    setFormData({
      smtp_server: config.smtp_server || "",
      smtp_port: config.smtp_port || 587,
      username: config.username || "",
      password: "", // Don't prefill password
      sender_email: config.sender_email || "",
      sender_name: config.sender_name || "",
      use_tls: config.use_tls !== undefined ? config.use_tls : true,
      use_ssl: config.use_ssl !== undefined ? config.use_ssl : false
    });
  };

  const handleDelete = async (configId) => {
    if (window.confirm("Are you sure you want to delete this email configuration?")) {
      try {
        await deleteEmailConfig(configId);
        onRefresh();
      } catch (error) {
        console.error("Error deleting email config:", error);
        alert("Failed to delete email configuration: " + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === "checkbox" ? checked : value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const form = new FormData();
      Object.keys(formData).forEach(key => {
        form.append(key, formData[key]);
      });

      if (editingConfig) {
        await updateEmailConfig(editingConfig.id, form);
      } else {
        await addEmailConfig(form);
      }
      
      setIsAdding(false);
      setEditingConfig(null);
      onRefresh();
    } catch (error) {
      console.error("Error saving email config:", error);
      alert("Failed to save email configuration: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingConfig(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Email Configuration</h2>
        <button
          className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
          onClick={handleAddNew}
        >
          Add New Configuration
        </button>
      </div>

      {(isAdding || editingConfig) && (
        <div className="bg-green-900/30 border border-green-700 rounded p-4 mb-6">
          <h3 className="text-lg font-bold mb-3">
            {editingConfig ? "Edit Email Configuration" : "Add New Email Configuration"}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">SMTP Server *</label>
                <input
                  type="text"
                  name="smtp_server"
                  value={formData.smtp_server}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">SMTP Port *</label>
                <input
                  type="number"
                  name="smtp_port"
                  value={formData.smtp_port}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Username *</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Password *</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required={!editingConfig} // Required when adding, optional when editing
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Sender Email *</label>
                <input
                  type="email"
                  name="sender_email"
                  value={formData.sender_email}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Sender Name</label>
                <input
                  type="text"
                  name="sender_name"
                  value={formData.sender_name}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                />
              </div>
            </div>
            
            <div className="flex items-center mb-4">
              <div className="flex items-center mr-6">
                <input
                  type="checkbox"
                  name="use_tls"
                  checked={formData.use_tls}
                  onChange={handleChange}
                  className="mr-2"
                  disabled={formData.use_ssl}
                />
                <label className="text-sm">Use TLS</label>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  name="use_ssl"
                  checked={formData.use_ssl}
                  onChange={handleChange}
                  className="mr-2"
                  disabled={formData.use_tls}
                />
                <label className="text-sm">Use SSL</label>
              </div>
            </div>

            <div className="flex space-x-2">
              <button
                type="submit"
                className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
              >
                {editingConfig ? "Update Configuration" : "Add Configuration"}
              </button>
              <button
                type="button"
                className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded"
                onClick={handleCancel}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full bg-green-900/30 border border-green-700">
          <thead>
            <tr className="bg-green-800/50">
              <th className="py-2 px-4 text-left">SMTP Server</th>
              <th className="py-2 px-4 text-left">Port</th>
              <th className="py-2 px-4 text-left">Username</th>
              <th className="py-2 px-4 text-left">Sender Email</th>
              <th className="py-2 px-4 text-left">Sender Name</th>
              <th className="py-2 px-4 text-left">Security</th>
              <th className="py-2 px-4 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {emailConfigs.map((config) => (
              <tr key={config.id} className="border-t border-green-700 hover:bg-green-800/30">
                <td className="py-2 px-4">{config.smtp_server}</td>
                <td className="py-2 px-4">{config.smtp_port}</td>
                <td className="py-2 px-4">{config.username}</td>
                <td className="py-2 px-4">{config.sender_email}</td>
                <td className="py-2 px-4">{config.sender_name || "-"}</td>
                <td className="py-2 px-4">
                  {config.use_tls ? "TLS" : config.use_ssl ? "SSL" : "None"}
                </td>
                <td className="py-2 px-4">
                  <button
                    className="text-blue-400 hover:text-blue-300 mr-2"
                    onClick={() => handleEdit(config)}
                  >
                    Edit
                  </button>
                  <button
                    className="text-red-400 hover:text-red-300"
                    onClick={() => handleDelete(config.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {emailConfigs.length === 0 && (
              <tr>
                <td colSpan="7" className="py-4 px-4 text-center">
                  No email configurations found. Add a new configuration to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EmailConfigSection;