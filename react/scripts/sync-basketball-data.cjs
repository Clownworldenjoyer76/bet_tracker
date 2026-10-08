const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const source = path.join(root,"..","app","frontend","src","assets","js","pages","basketball_dashboard.js");
const output = path.join(root,"src","data","basketball-dashboard.json");

const text = fs.readFileSync(source,"utf8");
const match = text.match(/const ALL_DATA = (\{[\s\S]*?\});\s*document\.addEventListener/);

if (!match) throw new Error("ALL_DATA not found in basketball_dashboard.js");

const data = JSON.parse(match[1]);
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(data,null,2)+"\n");
console.log("Basketball data written:",output);