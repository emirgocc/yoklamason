import React from 'react';

const AdminTabs = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { name: 'Dersler', icon: 'fa-book' },
    { name: 'Öğretmenler', icon: 'fa-chalkboard-teacher' },
    { name: 'Öğrenciler', icon: 'fa-user-graduate' },
    { name: 'Yoklama Verileri', icon: 'fa-clipboard-list' },
  ];

  return (
    <div className="container section pb-0 pt-5">
      <div className="tabs is-boxed">
        <ul>
          {tabs.map((tab, index) => (
            <li key={index} className={activeTab === index ? "is-active" : ""}>
              <a onClick={() => setActiveTab(index)}>
                <span className="icon is-small"><i className={`fas ${tab.icon}`}></i></span>
                <span>{tab.name}</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default AdminTabs;